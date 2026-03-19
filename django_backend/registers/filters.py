import django_filters
from .models import Register

class RegisterFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    credit = django_filters.BooleanFilter(field_name='credit')
    debit = django_filters.DateFilter(field_name='debit')

    class Meta:
        model = Register
        fields = {
            'name',
            'credit',
            'debit'
        }
            