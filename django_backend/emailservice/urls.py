from django.urls import path
from . import api

urlpatterns = [
    path('admin/otp/', api.OTPAdminView.as_view(), name='admin-email-otp'),
    path('admin/welcome/', api.WelcomeAdminView.as_view(), name='admin-email-welcome'),
    path('admin/subscription-update/', api.SubscriptionUpdateAdminView.as_view(), name='admin-email-sub-update'),
    path('admin/subscription-expiry/', api.SubscriptionExpiryAdminView.as_view(), name='admin-email-sub-expiry'),
]
