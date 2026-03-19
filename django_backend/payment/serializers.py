from rest_framework import serializers
from .models import Plan, Order
from decimal import Decimal
from django.contrib.auth import get_user_model

User = get_user_model()


class OrderSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    plan = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.all(), required=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'user',
            'plan',
            'order_id',
            'amount',
            'status',
            'currency',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate_amount(self, value):
        if value <= Decimal('0.00'):
            raise serializers.ValidationError("Amount must be greater than zero")
        return value

    def validate(self, data):
        # Validate required fields
        required_fields = ['amount', 'plan']
        missing_fields = {
            field: f"{field.replace('_', ' ').title()} is required"
            for field in required_fields
            if field not in data
        }

        if missing_fields:
            raise serializers.ValidationError(missing_fields)

        return data


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            'id',
            'name',
            'plan_id',
            'price',
            'duration_days',
            'duration_months',
            'duration_years',
            'savings',
            'active',
            'limited',
            'description',
        ]
        read_only_fields = ['id']
    