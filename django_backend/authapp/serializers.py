from rest_framework import serializers
from .models import User, ReferralCode
from django.core.exceptions import ValidationError

class SignupSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
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
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'verified', 'register_types', 'otp_verification', "first_opening_balance", 'first_opening_balance_date']
