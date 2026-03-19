from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from django.core.cache import cache
from django.db import transaction as db_transaction
from core.authentication import JWTAuthentication
from core.date_validators import validate_query_dates, DateValidationError, create_date_error_response
from .models import Journal
from .serializers import JournalSerializer
from .filters import JournalFilter
from decimal import Decimal
from core.journal_update import create_journal_from_date, get_full_journal_data, update_journal_for_date
from rest_framework.exceptions import ValidationError


class JournalViewSet(ViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = JournalFilter

    def list(self, request):
        user = request.user
        if not user.first_opening_balance_date:
            return Response({
                "status": False,
                "message": "Set first opening balance first."
            }, status=400)
        
        # Get query params
        single_date_str = request.query_params.get("date", "")
        start_date_str = request.query_params.get("start_date", "")
        end_date_str = request.query_params.get("end_date", "")
        
        # Validate dates using utility function (validates BEFORE any DB queries)
        try:
            dates = validate_query_dates(
                single_date_str=single_date_str or None,
                start_date_str=start_date_str or None,
                end_date_str=end_date_str or None,
                min_allowed_date=user.first_opening_balance_date,
                max_days_range=365,
                allow_future=False,
                min_date_context="first opening balance date"
            )
            parsed_single = dates['single_date']
            parsed_start = dates['start_date']
            parsed_end = dates['end_date']
        except DateValidationError as e:
            return create_date_error_response(e)
        
        # Generate cache key based on user and validated query params
        cache_key = f"journal_list_user_{user.id}_{single_date_str}_{start_date_str}_{end_date_str}"
        
        # Try to get cached data
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        
        # Now fetch journals from database with validated dates
        journals = Journal.objects.filter(user=user).select_related('user')
        
        if not journals.exists():
            return Response({
                "status": False,
                "message": "No journals found for this user."
            }, status=400)

        # Apply date filters with already-validated dates
        if parsed_single:
            journals = journals.filter(date=parsed_single)
        elif parsed_start and parsed_end:
            journals = journals.filter(date__range=[parsed_start, parsed_end])
        elif parsed_start:
            journals = journals.filter(date__gte=parsed_start)
        elif parsed_end:
            journals = journals.filter(date__lte=parsed_end)

        if journals.count() == 0:
            return Response({
                "status": False,
                "message": "No journals found for the specified date or range."
            }, status=404)

        journals = journals.order_by('date')

        response_data = get_full_journal_data(journals, user)
        response_data["status"] = True
        response_data["message"] = "Journals retrieved successfully."
        
        # Cache the response data for 5 minutes (300 seconds)
        cache.set(cache_key, response_data, 300)
        
        return Response(response_data)

    def create(self, request):
        user = request.user
        date_str = request.data.get('date')
        opening_balance = request.data.get('opening_balance')

        if(not user.subscription_active):
            raise ValidationError("Valid subscription required for this operation")
        if not date_str:
            return Response({"status": False, "message": "'date' is required."}, status=400)

        # Validate date using utility function (allows future dates for initial setup)
        try:
            from core.date_validators import validate_single_date_param
            date = validate_single_date_param(
                date_str, 
                min_allowed_date=None,  # No minimum for first journal creation
                allow_future=True,  # Allow future dates for initial setup
                param_name="date"
            )
        except DateValidationError as e:
            return create_date_error_response(e)

        # parse opening_balance to Decimal; allow zero
        try:
            opening_balance_dec = Decimal(str(opening_balance))
        except Exception:
            return Response({"status": False, "message": "Invalid opening_balance. Provide a numeric value."}, status=400)

        if Journal.objects.filter(user=user).exists():
            return Response({
                "status": False,
                "message": f"Journal already exists for this user."
            }, status=409)
        
        # Wrap in atomic transaction to ensure all-or-nothing behavior
        with db_transaction.atomic():
            user.first_opening_balance = opening_balance_dec
            user.first_opening_balance_date = date
            user.save()

            # create journals from provided date until today using Decimal
            result = create_journal_from_date(user, date, opening_balance=opening_balance_dec)

            if not result["status"]:
                return Response({
                    "status": False,
                    "message": result["message"]
                }, status=400)

            # Invalidate all journal cache for this user
            cache.delete_pattern(f"journal_list_user_{user.id}_*")

            # serialize all created journals
            serializer = JournalSerializer(result["journals"], many=True)

            return Response({
                "status": True,
                "message": result["message"],
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
    
    def update(self, request):
        user = request.user
        opening_balance = request.data.get("opening_balance")
        date_str = request.data.get('date')
        if not date_str:
            return Response({"status": False, "message": "'date' is required."}, status=400)

        # Validate date using utility function (allows future dates for updates)
        try:
            from core.date_validators import validate_single_date_param
            date = validate_single_date_param(
                date_str, 
                min_allowed_date=None,
                allow_future=True,  # Allow future dates for journal updates
                param_name="date"
            )
        except DateValidationError as e:
            return create_date_error_response(e)

        if not user.subscription_active:
            raise ValidationError("Valid subscription required for this operation")

        # parse opening_balance
        try:
            opening_balance_dec = Decimal(str(opening_balance))
        except Exception:
            return Response({"status": False, "message": "Invalid opening_balance. Provide a numeric value."}, status=400)

        # Ensure first opening date exists
        first_date = user.first_opening_balance_date
        if not first_date:
            return Response({"status": False, "message": "No journal found for this user."}, status=404)

        # Only allow update when the provided date matches the recorded first_opening_balance_date
        if first_date != date:
            return Response({"status": False, "message": "Date must match your first opening balance date to update."}, status=400)

        # Wrap in atomic transaction
        with db_transaction.atomic():
            # update user and refresh journals for that date
            user.first_opening_balance = opening_balance_dec
            user.save()
            update_journal_for_date(user, date=date)
            
            # Invalidate all journal cache for this user
            cache.delete_pattern(f"journal_list_user_{user.id}_*")
        
        return Response({"status": True, "message": "Journal updated with new opening balance successfully."}, status=status.HTTP_200_OK)