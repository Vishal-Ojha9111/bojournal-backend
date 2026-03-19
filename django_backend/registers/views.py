from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from django.db import transaction as db_transaction
from core.authentication import JWTAuthentication
from rest_framework.exceptions import ValidationError
from .models import Register
from .serializers import RegisterSerializer
from .filters import RegisterFilter
from django_filters.rest_framework import DjangoFilterBackend
from transactions.models import Transaction




class RegisterViewSet(ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filterset_class = RegisterFilter
    serializer_class = RegisterSerializer
    filter_backends = [DjangoFilterBackend]
    queryset = Register.objects.all()

    def get_queryset(self):
        user = self.request.user
        # Generate cache key for this user's register list
        cache_key = f"register_list_user_{user.id}"
        
        # Try to get cached queryset IDs
        cached_ids = cache.get(cache_key)
        if cached_ids:
            # Return queryset filtered by cached IDs
            return self.queryset.filter(id__in=cached_ids, user=user).order_by('-created_at', 'id')
        
        # Get fresh queryset
        queryset = self.queryset.filter(user=user).order_by('-created_at', 'id')
        # Cache the IDs for 10 minutes (600 seconds)
        register_ids = list(queryset.values_list('id', flat=True))
        cache.set(cache_key, register_ids, 600)
        
        return queryset

    def create(self, request):
        user = request.user
        data = request.data.copy()
        if(not user.subscription_active):
            raise ValidationError("Valid subscription required for this operation")
        # normalize name for consistent uniqueness check
        name = (data.get('name') or '').strip()
        if not name:
            raise ValidationError('Name is required')
        if Register.objects.filter(user=user, name__iexact=name).exists():
            raise ValidationError("Register with this name already exists.")
        
        # Wrap in atomic transaction
        with db_transaction.atomic():
            # rely on serializer HiddenField(CurrentUserDefault) and/or pass user when saving
            serializer = RegisterSerializer(data=data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save(user=user)
            
            # Invalidate register cache for this user
            cache.delete(f"register_list_user_{user.id}")
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, pk=None):
        if(not request.user.subscription_active):
            raise ValidationError("Valid subscription required for this operation")
        try:
            original = Register.objects.get(id=pk, user=request.user)
        except Register.DoesNotExist:
            raise ValidationError("Register not found")

        update = request.data.copy()
        serializer = RegisterSerializer(original, data=update, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)

        validated = serializer.validated_data

        # compute new effective values (fall back to original when not provided)
        new_name = validated.get('name', original.name)
        new_debit = validated.get('debit', original.debit)
        new_credit = validated.get('credit', original.credit)
        new_description = validated.get('description', original.description)

        # ensure at least one of debit/credit
        if not new_debit and not new_credit:
            raise ValidationError("At least one of debit or credit must be allowed.")

        # detect no changes
        if (original.name.lower() == (new_name or '').lower() and original.debit == new_debit and original.credit == new_credit and (original.description or '') == (new_description or '')):
            raise ValidationError("No changes detected.")

        # uniqueness only if name changed
        if new_name and new_name.lower() != original.name.lower() and Register.objects.filter(user=request.user, name__iexact=new_name).exclude(id=original.id).exists():
            raise ValidationError("Register with this name already exists.")

        # Only check transaction conflicts when a permission (debit/credit) is being removed
        if (original.debit and not new_debit):
            if Transaction.objects.filter(user=request.user, register=original, transaction_type='debit').exists():
                raise ValidationError(f"Cannot change register. There are existing debit transactions associated with this register.")
        if (original.credit and not new_credit):
            if Transaction.objects.filter(user=request.user, register=original, transaction_type='credit').exists():
                raise ValidationError(f"Cannot change register. There are existing credit transactions associated with this register.")

        # Wrap in atomic transaction
        with db_transaction.atomic():
            serializer.save()
            
            # Invalidate register cache for this user
            cache.delete(f"register_list_user_{request.user.id}")
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
    def destroy(self, request, pk=None):
        user = request.user
        if(not user.subscription_active):
            raise ValidationError("Valid subscription required for this operation")
        try:
            instance = Register.objects.get(id=pk, user=user)
        except Register.DoesNotExist: 
            raise ValidationError("Register not found")
        transactions = Transaction.objects.filter(user=user, register=instance)
        if transactions.exists():
            raise ValidationError("Cannot delete register with existing transactions.")
        
        # Wrap in atomic transaction
        with db_transaction.atomic():
            instance.delete()
            
            # Invalidate register cache for this user
            cache.delete(f"register_list_user_{user.id}")
        
        return Response(status=status.HTTP_204_NO_CONTENT)

