from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from journal.models import Journal
from .serializers import HolidaySerializer
from rest_framework.permissions import IsAuthenticated
from core.authentication import JWTAuthentication
from core.date_validators import (
    validate_query_dates, 
    validate_single_date_param,
    DateValidationError, 
    create_date_error_response
)

class HolidayView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get query params
        single_date_str = request.query_params.get("date")
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        # Validate dates using utility function
        try:
            dates = validate_query_dates(
                single_date_str=single_date_str,
                start_date_str=start_date_str,
                end_date_str=end_date_str,
                min_allowed_date=None,  # No minimum for holidays (can view past holidays)
                max_days_range=730,  # Allow 2 years for holiday queries
                allow_future=True,  # Allow viewing future holidays
                min_date_context="allowed date"
            )
            parsed_single = dates['single_date']
            parsed_start = dates['start_date']
            parsed_end = dates['end_date']
        except DateValidationError as e:
            return create_date_error_response(e)

        # Query holidays with validated dates
        journals = Journal.objects.filter(user=request.user, is_holiday=True)

        if parsed_single:
            journals = journals.filter(date=parsed_single)
        elif parsed_start and parsed_end:
            journals = journals.filter(date__range=[parsed_start, parsed_end])
        elif parsed_start:
            journals = journals.filter(date__gte=parsed_start)
        elif parsed_end:
            journals = journals.filter(date__lte=parsed_end)

        journals = journals.order_by("date")

        if not journals.exists():
            return Response({
                "status": True,
                "message": "No holidays available.",
                "data": []
            })

        serializer = HolidaySerializer(journals, many=True)
        return Response({
            "status": True,
            "message": "Holidays fetched successfully.",
            "data": serializer.data
        })


    def post(self, request):
        date_str = request.data.get("date")
        reason = request.data.get("reason")

        if not date_str or not reason:
            return Response({
                "status": False,
                "message": "Both 'date' and 'reason' are required."
            }, status=400)

        # Validate date using utility function (allow future dates for holiday planning)
        try:
            date = validate_single_date_param(
                date_str,
                min_allowed_date=None,  # No minimum date restriction for holidays
                allow_future=True,  # Allow future holiday planning
                param_name="date"
            )
        except DateValidationError as e:
            return create_date_error_response(e)

        isJournal = Journal.objects.filter(user=request.user)

        if not isJournal.exists():
            return Response({
                "status": False,
                "message": "No journal found to mark holiday."
            })

        journal = Journal.objects.filter(user=request.user,date=date).first()

        if(journal and journal.is_holiday):
            return Response({
                "status":False,
                "message":"Already marked as holiday"
            },status=500)
        

        today = timezone.localtime().date()

        # If date is today or future
        if date >= today:
            if date.weekday() == 6: 
                return Response({
                    "status": False,
                    "message": "Cannot mark a holiday on a Sunday."
                }, status=400)
            journal, created = Journal.objects.get_or_create(user=request.user, date=date)
            if created or journal.opening_balance == journal.closing_balance:
                journal.is_holiday = True
                journal.holiday_reason = reason
                journal.save()

                return Response({
                    "status": True,
                    "message": f"Holiday marked on {date}."
                }, status=201)
           

        # If date is in the past
        journal = Journal.objects.filter(user=request.user, date=date).first()
        if journal and journal.opening_balance != journal.closing_balance:
            return Response({
                "status": False,
                "message": f"Cannot mark holiday on {date}, transactions already exist."
            }, status=404)

        journal.user = request.user
        journal.is_holiday = True
        journal.holiday_reason = reason
        journal.save()

        return Response({
            "status": True,
            "message": f"Holiday updated for {date}."
        }, status=200)


    def delete(self, request):
        date_str = request.data.get("date")
        if not date_str:
            return Response({
                "status": False,
                "message": "Date is required to delete a holiday."
            }, status=400)

        # Validate date using utility function (allow future dates)
        try:
            date = validate_single_date_param(
                date_str,
                min_allowed_date=None,  # No minimum date restriction
                allow_future=True,  # Allow deleting future holidays
                param_name="date"
            )
        except DateValidationError as e:
            return create_date_error_response(e)

        today = timezone.localtime().date()
        journal = Journal.objects.filter(user=request.user, date=date).first()
        if not journal or not journal.is_holiday:
            return Response({
                "status": False,
                "message": f"No holiday found for {date}."
            }, status=404)

        if date > today:
            journal.delete()
            return Response({
                "status": True,
                "message": f"Future holiday on {date} deleted."
            }, status=200)
        
        if date.weekday()==6:
            return Response({
                "status": False,
                "message": f"Cannot remove holiday for {date} as it is a Sunday."
            }, status=400)
        
        journal.is_holiday = False
        journal.holiday_reason = ""
        journal.save()

        return Response({
            "status": True,
            "message": f"Holiday removed for {date}."
        }, status=200)
