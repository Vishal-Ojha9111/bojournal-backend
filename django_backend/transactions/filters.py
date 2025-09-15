import django_filters
from .models import Transaction

class TransactionFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='date', lookup_expr='exact')
    start_date = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='date', lookup_expr='lte')

    amount = django_filters.NumberFilter(field_name='amount', lookup_expr='exact')
    min_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    max_amount = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')

    transaction_type = django_filters.CharFilter(field_name='transaction_type', lookup_expr='iexact')
    register = django_filters.CharFilter(field_name='register', lookup_expr='iexact')

    class Meta:
        model = Transaction
        fields = {
            'date',
            'amount',
            'transaction_type',
            'register'
        }

