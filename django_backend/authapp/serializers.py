from registers.models import Register
from rest_framework import serializers
from .models import User, ReferralCode
from django.core.exceptions import ValidationError
from django.conf import settings
import logging

# local import to generate presigned view URLs for profile pictures
from core.s3_utils import generate_presigned_view_url

logger = logging.getLogger(__name__)



class SignupSerializer(serializers.Serializer):
    # Make first_name and last_name explicitly required for signup
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    referral_code = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)

    def validate_referral_code(self, value):
        if not value or value.strip() == "" or value is None:
            return value
            
        try:
            referral = ReferralCode.objects.get(code=value)
            if not referral.is_valid():
                raise ValidationError("This referral code is no longer valid")
            return value
        except ReferralCode.DoesNotExist:
            raise ValidationError("Invalid referral code")

class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class UserSerializer(serializers.ModelSerializer):
    first_opening_balance = serializers.DecimalField(
        max_digits=10, decimal_places=2, coerce_to_string=False
    )
    register_types = serializers.SerializerMethodField()
    profile_picture_url = serializers.SerializerMethodField()
    subscription_plan = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'referral_code', 'subscription_active',
            'subscription_start_date', 'subscription_end_date', 'subscription_plan', 'register_types', 'otp_verification',
            'first_opening_balance', 'first_opening_balance_date', 'profile_picture_url'
        ]

    def get_register_types(self, obj):
        registers = Register.objects.filter(user=obj).values("id", "name", "debit","credit")
        return [{"id": r["id"], "register_name": r["name"], "debit": r["debit"], "credit": r["credit"]} for r in registers]

    def get_profile_picture_url(self, obj):
        """
        Return a presigned URL for the user's profile picture key if present.
        If S3 is not configured or any error occurs, return None.
        TTL can be configured via settings.PROFILE_PICTURE_URL_EXPIRES (seconds) or falls back to AWS_PRESIGNED_URL_EXPIRES or 600s.
        """
        key = getattr(obj, 'profile_picture_key', None)
        if not key:
            return None

        # allow either a string key or a dict containing the key (if stored as JSON)
        if isinstance(key, dict):
            # try common fields
            possible = [key.get('key'), key.get('s3_key'), key.get('object_key')]
            key = next((p for p in possible if p), None)

        if not key or (isinstance(key, str) and key.strip() == ''):
            return None

        expires = getattr(settings, 'PROFILE_PICTURE_URL_EXPIRES', None)
        if expires is None:
            expires = getattr(settings, 'AWS_PRESIGNED_URL_EXPIRES', 600)

        try:
            return generate_presigned_view_url(key=key, expires_in=int(expires))
        except Exception as e:
            logger.exception("Failed to generate presigned profile picture URL for user %s: %s", getattr(obj, 'email', '<unknown>'), e)
            return None

    def get_subscription_plan(self, obj):
        """
        Return the subscription plan details for the user if active.
        """
        if obj.subscription_active and obj.subscription_plan:
            return {
                "plan_id": obj.subscription_plan.plan_id,
                "name": obj.subscription_plan.name,
                "price": obj.subscription_plan.price,
                "duration_days": obj.subscription_plan.duration_days,
                "duration_months": obj.subscription_plan.duration_months,
                "duration_years": obj.subscription_plan.duration_years,
                "savings": obj.subscription_plan.savings,
                "description": obj.subscription_plan.description,
            }
        return None