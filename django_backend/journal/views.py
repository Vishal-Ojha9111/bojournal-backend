from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from django.utils.dateparse import parse_date
from core.authentication import JWTAuthentication
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
        journals = Journal.objects.filter(user=user)

        if not journals.exists():
            return Response({
                "status": False,
                "message": "No journals found for this user."
            }, status=400)

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        single_date = request.query_params.get("date")

        if single_date:
            journals = journals.filter(date=single_date)
        elif start_date and end_date:
            journals = journals.filter(date__range=[start_date, end_date])
        elif start_date:
            journals = journals.filter(date__gte=start_date)
        elif end_date:
            journals = journals.filter(date__lte=end_date)

        if journals.count() == 0:
            return Response({
                "status": False,
                "message": "No journals found for the specified date or range."
            }, status=404)

        journals = journals.order_by('date')

        response_data = get_full_journal_data(journals, user)
        response_data["status"] = True
        response_data["message"] = "Journals retrieved successfully."
        return Response(response_data)

    def create(self, request):
        user = request.user
        date_str = request.data.get('date')
        opening_balance = request.data.get('opening_balance')

        if(not user.verified):
            raise ValidationError("Please contact developer to verify your account.")
        
        if not date_str or not opening_balance or opening_balance < 0:
            return Response({
                "status": False,
                "message": "Both 'date' and 'opening_balance' are required."
            }, status=400)

        date = parse_date(date_str)
        if not date:
            return Response({
                "status": False,
                "message": "Invalid date format. Use YYYY-MM-DD."
            }, status=400)

        if Journal.objects.filter(user=user).exists():
            return Response({
                "status": False,
                "message": f"Journal already exists for this user."
            }, status=409)

        user.first_opening_balance = Decimal(opening_balance)
        user.first_opening_balance_date = date
        user.save()

        result = create_journal_from_date(user, date, opening_balance=Decimal(opening_balance))

        if not result["status"]:
            return Response({
                "status": False,
                "message": result["message"]
            }, status=400)

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
        if not date_str or opening_balance < 0:
            return Response({
                "status": False,
                "message": "Both 'date' and 'opening_balance' are required."
            }, status=400)

        date = parse_date(date_str)

        journal = Journal.objects.filter(user=user).order_by('date').first()

        if not journal:
            return Response({
                "status": False,
                "message": "No journal found for this user."
            }, status=404)
        if journal.date > date:
            return Response({
                "status": False,
                "message": "Cannot update journal for a date in the past of first entry."
                }, status=400)

        if journal.date == date:
            user.first_opening_balance = opening_balance
            user.save()
            update_journal_for_date(user,date=date)
            return Response({
                "status": True,
                "message": "Journal updated with new opening balance successfully."
                }, status=status.HTTP_200_OK)

        if journal.date < date:
            return Response({
                "status": False,
                "message": "Cannot update already created journal. Please add transactions to auto update."
            },status=400)