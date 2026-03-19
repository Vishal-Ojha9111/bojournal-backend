from django.urls import path
from .views import (
    CancelOrderView,
    GetOrderView,
    VerifyPaymentView,
    PaymentHistoryView,
    PaymentStatusView,
    CreateOrderView,
    PlanDetailView,
    PlanListView,
)

app_name = 'payment'

urlpatterns = [
    # Payment routes
    path('createorder/<int:planId>/', CreateOrderView.as_view(), name='create_order'),
    path('verify/', VerifyPaymentView.as_view(), name='verify_payment'),
    path('history/', PaymentHistoryView.as_view(), name='get_history'),
    path('status/<int:planId>/', PaymentStatusView.as_view(), name='get_payment_status'),
    path('getorder/<str:orderId>/', GetOrderView.as_view(), name='get_order'),
    path('cancel/<str:orderId>/', CancelOrderView.as_view(), name='cancel_order'),

    # Plan routes
    path('plan/<int:id>/', PlanDetailView.as_view(), name='get_plan_details'),
    path('plans/', PlanListView.as_view(), name='get_all_plans'),
]
