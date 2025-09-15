from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Transaction
from .serializers import TransactionSerializer
from .filters import TransactionFilter
from core.authentication import JWTAuthentication
from core.journal_update import update_journal_for_date
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from journal.models import Journal
from rest_framework.views import APIView
from rest_framework.response import Response
from core.s3_utils import generate_presigned_upload_url, delete_s3_objects


class TransactionsListView(ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = TransactionFilter
    serializer_class = TransactionSerializer
    queryset = Transaction.objects.all()
    
    def get_queryset(self):
        return self.queryset.filter(user=self.request.user).order_by('-date')


    def perform_create(self, serializer):
        user = self.request.user
        tx_date = serializer.validated_data.get('date') 
        register_type = serializer.validated_data.get('register')
        today = timezone.localtime().date()

        if(not user.verified):
            raise ValidationError("Please contact developer to verify your account.")

        if tx_date > today:
            raise ValidationError("Cannot create transactions for future dates")

        journal = Journal.objects.filter(user=user, date=tx_date).first()

        if not journal:
            j = Journal.objects.filter(user=user).first()
            raise ValidationError(f"Cannot create transaction before first entry of journal. Create transaction from or after date {j.date}")

        if journal and journal.is_holiday:
            reason = journal.holiday_reason or "No reason provided"
            raise ValidationError(f"Cannot create transactions on a holiday: {reason}")

        # Add register_type to user's register_types if not present
        if register_type and register_type not in user.register_types:
            user.register_types.append(register_type)
            user.save()

        serializer.save(user=user)
        update_journal_for_date(user, tx_date)
    
    def perform_update(self, serializer):
        original = self.get_object()
        user = self.request.user
        update_data = self.request.data


        # Get updated values from validated data
        new_date = serializer.validated_data.get('date', original.date)
        new_register = serializer.validated_data.get('register', original.register)
        new_image_keys = serializer.validated_data.get('image_keys', original.image_keys)

        # Check for future date
        today = timezone.localdate()
        if new_date > today:
            raise ValidationError("Cannot set transaction date to the future.")

        # Check for holiday
        journal = Journal.objects.filter(user=user, date=new_date).first()
        if journal and journal.is_holiday:
            reason = journal.holiday_reason or "No reason provided"
            raise ValidationError(f"Cannot update transaction on a holiday: {reason}")
        
        # Register type update
        if new_register != original.register:
            if new_register not in user.register_types:
                user.register_types.append(new_register)
                user.save()

        if new_image_keys is not None and new_image_keys != original.image_keys:
            if original.image_keys:
                delete_s3_objects(original.image_keys)
            

        # Save the updated transaction
        updated = serializer.save()

        # Update affected journals
        if original.date <= new_date:
            update_journal_for_date(user, original.date)
        update_journal_for_date(user, updated.date)

        

    def perform_destroy(self, instance):
        date = instance.date
        if instance.image_keys:
            delete_s3_objects(instance.image_keys)
        instance.delete()
        update_journal_for_date(self.request.user, date)



class PresignedURLView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        content_type = request.data.get("content_type")
        extension = request.data.get("extension")
        if not content_type or not extension:
            return Response({"error": "Missing content_type or extension"}, status=400)

        result = generate_presigned_upload_url(content_type, extension)
        return Response(result)

    
class CleanupViewSet(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        keys = request.data.get("keys", [])
        delete_s3_objects(keys)

        return Response({"message": "All transactions deleted successfully"}, status=200)


