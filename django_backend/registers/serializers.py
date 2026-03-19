from rest_framework import serializers
from .models import Register
from django.contrib.auth import get_user_model
from rest_framework.fields import CurrentUserDefault


User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    # user is set by the view via serializer.save(user=request.user) or using CurrentUserDefault in context
    user = serializers.HiddenField(default=CurrentUserDefault())
    name = serializers.CharField(max_length=255, required=True)
    credit = serializers.BooleanField(required=True)
    debit = serializers.BooleanField(required=True)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Register
        fields = ['id', 'user', 'name', 'credit', 'debit', 'description']

    def validate_name(self, value: str) -> str:
        # Normalize name to lowercase and strip whitespace for consistent uniqueness checks
        if value:
            return value.strip().lower()
        return value