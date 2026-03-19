from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .dispatcher import enqueue_email
from .serializers import AdminEmailSerializer, AdminOTPSerializer


class BaseAdminEmailView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        self.enqueue(data)
        return Response({'ok': True})


class OTPAdminView(BaseAdminEmailView):
    def get_serializer(self, *args, **kwargs):
        return AdminOTPSerializer(*args, **kwargs)

    def enqueue(self, data):
        meta = data.get('data', {})
        meta['otp'] = data.get('otp')
        enqueue_email('otp', data['to_email'], data=meta, priority='critical', locale=data.get('locale', 'en'))


class WelcomeAdminView(BaseAdminEmailView):
    def get_serializer(self, *args, **kwargs):
        return AdminEmailSerializer(*args, **kwargs)

    def enqueue(self, data):
        # Welcome emails have lowest priority (user doesn't need immediate info)
        enqueue_email('welcome', data['to_email'], data=data.get('data'), priority='low', locale=data.get('locale', 'en'))


class SubscriptionUpdateAdminView(BaseAdminEmailView):
    def get_serializer(self, *args, **kwargs):
        return AdminEmailSerializer(*args, **kwargs)

    def enqueue(self, data):
        # Subscription updates have high priority (important but not critical)
        enqueue_email('subscription_update', data['to_email'], data=data.get('data'), priority='high', locale=data.get('locale', 'en'))


class SubscriptionExpiryAdminView(BaseAdminEmailView):
    def get_serializer(self, *args, **kwargs):
        return AdminEmailSerializer(*args, **kwargs)

    def enqueue(self, data):
        # Subscription expiry warnings have high priority (sent in bulk at midnight)
        enqueue_email('subscription_expiry', data['to_email'], data=data.get('data'), priority='high', locale=data.get('locale', 'en'))
