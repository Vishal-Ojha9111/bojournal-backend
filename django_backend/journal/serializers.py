from rest_framework import serializers
from .models import Journal
from django.contrib.auth import get_user_model

User = get_user_model()


class JournalSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)

    class Meta:
        model = Journal
        fields = [
            'id',
            'user',
            'opening_balance',
            'closing_balance',
            'created_at',
            'is_holiday',
            'holiday_reason',
            'date'
        ]
        read_only_fields = ['id', 'created_at']


