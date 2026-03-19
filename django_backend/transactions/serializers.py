from rest_framework import serializers
from .models import Transaction
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
from registers.models import Register

User = get_user_model()


class TransactionSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    register = serializers.PrimaryKeyRelatedField(queryset=Register.objects.all(), required=True)
    image_keys = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=False,
        default=list
    )
    image_urls = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            'id',
            'user',
            'amount',
            'transaction_type',
            'date',
            'register',
            'description',
            'created_at',
            'image_keys',
            'image_urls'
        ]
        read_only_fields = ['id', 'created_at', 'image_urls']

    def validate_amount(self,value):
        if value <= Decimal('0.00'):
            raise serializers.ValidationError("Amount must be greater than zero")
        return value

    def get_image_urls(self, obj):
        from core.s3_utils import generate_presigned_view_url
        if not obj.image_keys:
            return []
        return [generate_presigned_view_url(key) for key in obj.image_keys]

    def validate(self, data):
        # Validate required fields
        required_fields = ['amount', 'transaction_type', 'register', 'date']
        missing_fields = {
            field: f"{field.replace('_', ' ').title()} is required"
            for field in required_fields 
            if field not in data
        }
        
        if missing_fields:
            raise serializers.ValidationError(missing_fields)

        # Validate transaction type
        if data.get('transaction_type') and data['transaction_type'] not in ['credit', 'debit']:
            raise serializers.ValidationError(
                {"transaction_type": "Transaction type must be either credit or debit"}
            )

        return data

    def validate_date(self, value):
        if value > timezone.localtime().date():
            raise serializers.ValidationError("Cannot set transaction date to the future")
        return value



