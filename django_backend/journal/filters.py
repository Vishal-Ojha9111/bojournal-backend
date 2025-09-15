import django_filters
from .models import Journal


class JournalFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='date', lookup_expr='exact')
    start_date = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='date', lookup_expr='lte')

    class Meta:
        model = Journal
        fields = {
            'date',
        }