from rest_framework import serializers
from journal.models import Journal

class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Journal
        fields = ['date', 'is_holiday', 'holiday_reason']
