from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.dateparse import parse_date
from django.utils import timezone
from journal.models import Journal
from .serializers import HolidaySerializer
from rest_framework.permissions import IsAuthenticated
from core.authentication import JWTAuthentication

class HolidayView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        date = request.query_params.get("date")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        journals = Journal.objects.filter(user=request.user, is_holiday=True)

        if date:
            journals = journals.filter(user=request.user, is_holiday= True, date=parse_date(date))
        elif start_date and end_date:
            journals = journals.filter(user=request.user, is_holiday=True, date__range=[parse_date(start_date), parse_date(end_date)])
        elif start_date:
            journals = journals.filter(user=request.user, is_holiday=True, date__gte=start_date)

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

        date = parse_date(date_str)
        if not date:
            return Response({
                "status": False,
                "message": "Invalid date format. Use YYYY-MM-DD."
            }, status=400)

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

        date = parse_date(date_str)
        if not date:
            return Response({
                "status": False,
                "message": "Invalid date format. Use YYYY-MM-DD."
            }, status=400)

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
        
        if journal and journal.holiday_reason == "Sunday":
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
