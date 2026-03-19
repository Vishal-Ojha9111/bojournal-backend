from django_backend.settings import ALLOWED_IMAGE_KEYS
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.core.cache import cache
from .models import Transaction
from .serializers import TransactionSerializer
from .filters import TransactionFilter
from core.authentication import JWTAuthentication
from core.permissions import IsOwner
from core.journal_update import update_journal_for_date
from django.utils import timezone
from django.db import transaction as db_transaction
from rest_framework.exceptions import ValidationError
from journal.models import Journal
from rest_framework.views import APIView
from rest_framework.response import Response
from core.s3_utils import generate_presigned_upload_url, delete_s3_objects
from registers.models import Register


class RegisterNotFoundError(ValidationError):
    status_code = 404
    default_detail = "Register not found."
    default_code = "register_not_found"

class TransactionsView(ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsOwner]
    filter_backends = [DjangoFilterBackend]
    filterset_class = TransactionFilter
    serializer_class = TransactionSerializer
    queryset = Transaction.objects.all()
    
    def get_queryset(self):
        # Optimize with select_related to avoid N+1 queries for register and user ForeignKeys
        return self.queryset.filter(
            user=self.request.user
        ).select_related('user', 'register').order_by('-date', '-created_at')


    def perform_create(self, serializer):
        user = self.request.user
        tx_date = serializer.validated_data.get('date') 
        register_type = serializer.validated_data.get('register')
        today = timezone.localtime().date()
        transaction_type = serializer.validated_data.get('transaction_type')
        if(not user.subscription_active):
            raise ValidationError("Valid subscription required for this operation")

        if tx_date > today:
            raise ValidationError("Cannot create transactions for future dates")

        # Ensure user has a first journal entry and transaction date is not before it
        first_journal = Journal.objects.filter(user=user).order_by('date').first()
        if not first_journal:
            raise ValidationError("No journal found for user. Please create the first journal entry (opening balance) before creating transactions.")

        if tx_date < first_journal.date:
            raise ValidationError(f"Cannot create transaction before first entry of journal. Create transaction from or after date {first_journal.date}")

        journal = Journal.objects.filter(user=user, date=tx_date).first()

        if journal and journal.is_holiday:
            reason = journal.holiday_reason or "No reason provided"
            raise ValidationError(f"Cannot create transactions on a holiday: {reason}")


        user_registers = Register.objects.filter(user=user)
        if not user_registers.exists():
            raise RegisterNotFoundError('No registers found. Please create a register.')
        # register_type may be a Register instance or an id depending on serializer; ensure ownership
        reg_obj = None
        if isinstance(register_type, Register):
            reg_obj = register_type
        else:
            try:
                reg_obj = Register.objects.get(id=register_type)
            except Exception:
                raise RegisterNotFoundError('Register not found. Please create the register first.')

        if reg_obj.user_id != user.id:
            raise RegisterNotFoundError('Register not found or not owned by user.')
        if not ((reg_obj.debit is True and transaction_type == 'debit') or (reg_obj.credit is True and transaction_type == 'credit')):
            raise ValidationError(f"Register '{reg_obj.name}' does not support {transaction_type} transactions.")

        # Validate amount
        amount = serializer.validated_data.get('amount')
        if amount is None:
            raise ValidationError('Amount is required')
        try:
            # ensure positive
            if amount <= 0:
                raise ValidationError('Amount must be greater than zero')
        except TypeError:
            raise ValidationError('Invalid amount')
        # All validation passed — save transaction and update journal
        # Wrap in atomic transaction to ensure data consistency
        with db_transaction.atomic():
            saved = serializer.save(user=user)
            update_journal_for_date(user, tx_date)
            
            # Invalidate journal cache for this user
            cache.delete_pattern(f"journal_list_user_{user.id}_*")
        
        return saved
    
    @db_transaction.atomic
    def perform_update(self, serializer):
        original = self.get_object()
        user = self.request.user

        if(not user.subscription_active):
            raise ValidationError("Valid subscription required for this operation")
        
        # Get updated values from validated data
        new_date = serializer.validated_data.get('date', original.date)
        new_image_keys = serializer.validated_data.get('image_keys', original.image_keys)
        new_register = serializer.validated_data.get('register', original.register)
        transaction_type = serializer.validated_data.get('transaction_type', original.transaction_type)

        # Check for future date
        today = timezone.localtime().date()
        if new_date > today:
            raise ValidationError("Cannot set transaction date to the future.")

        # Check for holiday
        journal = Journal.objects.filter(user=user, date=new_date).first()
        if journal and journal.is_holiday:
            reason = journal.holiday_reason or "No reason provided"
            raise ValidationError(f"Cannot update transaction on a holiday: {reason}")

        if not ((new_register.debit is True and transaction_type == 'debit') or (new_register.credit is True and transaction_type == 'credit')):
            raise ValidationError(f"Register '{new_register.name}' does not support {transaction_type} transactions.")

        if new_image_keys is not None and new_image_keys != original.image_keys:
            if original.image_keys:
                delete_s3_objects(original.image_keys)
            

        # Save the updated transaction
        updated = serializer.save()

        # Update affected journals: always update both original date and updated date
        try:
            update_journal_for_date(user, original.date)
        except Exception:
            # swallow to avoid blocking the update; log in real app
            pass
        try:
            update_journal_for_date(user, updated.date)
        except Exception:
            pass
        
        # Invalidate journal cache for this user
        cache.delete_pattern(f"journal_list_user_{user.id}_*")

        

    @db_transaction.atomic
    def perform_destroy(self, instance):
        date = instance.date
        user = self.request.user
        
        # Delete S3 objects if present
        if instance.image_keys:
            delete_s3_objects(instance.image_keys)
        
        # Delete transaction and update journal
        instance.delete()
        update_journal_for_date(user, date)
        
        # Invalidate journal cache for this user
        cache.delete_pattern(f"journal_list_user_{user.id}_*")



class PresignedURLView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        content_type = request.data.get("content_type")
        extension = request.data.get("extension")
        key = request.data.get("key")
        # ensure user has valid subscription
        user = request.user
        if not getattr(user, 'subscription_active', False):
            return Response({"error": "Valid subscription required."}, status=403)
        
        # validate key prefix
        if key not in ALLOWED_IMAGE_KEYS:
            return Response({"error": "Invalid S3 key prefix."}, status=400)
        if not content_type or not extension:
            return Response({"error": "Missing content_type or extension"}, status=400)

        result = generate_presigned_upload_url(content_type, extension, key)
        return Response(result)

    
class CleanupViewSet(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        user = request.user
        if not getattr(user, 'subscription_active', False):
            return Response({"error": "Valid subscription required."}, status=403)

        keys = request.data.get("keys", [])
        if not isinstance(keys, (list, tuple)):
            return Response({"error": "keys must be a list of s3 keys"}, status=400)

        if not keys:
            return Response({"message": "No keys provided"}, status=400)

        try:
            delete_s3_objects(keys)
        except Exception:
            # best-effort; log exception in real app
            return Response({"error": "Failed to delete some objects"}, status=500)

        return Response({"message": "Transaction images deleted successfully"}, status=200)


