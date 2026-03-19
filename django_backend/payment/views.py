from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from core.authentication import JWTAuthentication
from .serializers import PlanSerializer, OrderSerializer

from django.shortcuts import get_object_or_404
from django.conf import settings

import razorpay
from datetime import date, timedelta, datetime

from .models import Plan, Order
from django.contrib.auth import get_user_model

User = get_user_model()


def _get_razorpay_client():
    key = getattr(settings, 'RAZORPAY_KEY', None) or settings.__dict__.get('RAZORPAY_KEY') or None
    secret = getattr(settings, 'RAZORPAY_SECRET', None) or settings.__dict__.get('RAZORPAY_SECRET') or None
    if not key or not secret:
        # fallback to environment if settings don't have them
        import os
        key = os.getenv('RAZORPAY_KEY')
        secret = os.getenv('RAZORPAY_SECRET')
    return razorpay.Client(auth=(key, secret))


def refresh_order_status(order, client=None, expire_after_hours=1):
    """Refresh and persist an Order's status from Razorpay.

    - order: Order instance to refresh
    - client: optional razorpay.Client; if None, will be created
    - expire_after_hours: age in hours after which an unpaid order should be marked expired

    Returns the (possibly updated) Order instance.
    This function is idempotent and swallows third-party errors to avoid breaking callers.
    """
    try:
        # create client lazily to avoid unnecessary network usage
        client = client or _get_razorpay_client()

        # If already paid or expired, nothing to do
        if order.status == 'paid' or order.expired:
            return order

        # expire orders older than configured threshold
        if datetime.now().astimezone() - order.created_at > timedelta(hours=expire_after_hours):
            order.expired = True
            order.save(update_fields=['expired'])
            return order

        # fetch remote order
        razorpay_order = client.order.fetch(order.order_id)
        if not razorpay_order:
            return order

        rp_status = razorpay_order.get('status')
        if rp_status and rp_status != order.status:
            order.status = rp_status
            order.attempts = razorpay_order.get('attempts', order.attempts)
            order.save(update_fields=['status', 'attempts'])
    except Exception:
        # silent fallback: don't break callers if third-party call fails
        pass
    return order


class PlanListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # Public endpoint
    serializer_class = PlanSerializer

    def get(self, request):
        plans = Plan.objects.all()
        if not plans.exists():
            return Response({'message': 'No plans available'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.serializer_class(plans, many=True)
        return Response({'message': 'All available plans retrieved successfully', 'plans': serializer.data}, status=status.HTTP_200_OK)


class PlanDetailView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # Public endpoint
    serializer_class = PlanSerializer

    def get(self, request, id):
        plan = get_object_or_404(Plan, id=id)
        serializer = self.serializer_class(plan)
        return Response({'message': 'Plan details retrieved successfully', 'plan': serializer.data}, status=status.HTTP_200_OK)


class CreateOrderView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = PlanSerializer

    def get(self, request, planId):
        user = request.user
        plan = get_object_or_404(Plan, id=planId)
        amount = plan.price
        client = _get_razorpay_client()
        receipt = f"receipt_{user.id}_{plan.id}_{datetime.now()}"
        discounted_amount = amount
        if user.referral_code and not user.referral_code_used:
            discounted_amount -= round((amount/100) * user.referral_code.discount_percentage)
        try:
            razorpay_order = client.order.create({
                'amount': discounted_amount if discounted_amount > 0 else amount,  # amount in paise
                'currency': 'INR',
                'receipt': receipt,
                'payment_capture': 1,
            })
        except Exception as e:
            return Response({'message': 'Failed to create razorpay order'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # persist order in DB
        order_obj = Order.objects.create(
            user=user,
            plan=plan,
            order_id=razorpay_order.get('id') if isinstance(razorpay_order, dict) else None,
            amount=discounted_amount if discounted_amount > 0 else amount,
            status='created',
            currency='INR',
        )

        return Response({
            'message': 'Order created',
            'order': {
                'id': order_obj.id,
                'order_id': order_obj.order_id,
                'amount': order_obj.amount,
                'discount': amount - discounted_amount if discounted_amount > 0 else amount,
                'currency': order_obj.currency,
                'plan' : PlanSerializer(order_obj.plan).data,
                'name': order_obj.plan.name,
                'key': _get_razorpay_client().auth[0],
                'description': order_obj.plan.description,
            },
        }, status=status.HTTP_201_CREATED)


class VerifyPaymentView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_signature = data.get('razorpay_signature')

        if not (razorpay_payment_id and razorpay_order_id and razorpay_signature):
            return Response({'message': 'Missing payment verification fields'}, status=status.HTTP_400_BAD_REQUEST)

        client = _get_razorpay_client()
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature,
            })
        except Exception as e:
            return Response({'message': 'Signature verification failed', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # find corresponding Order
        try:
            order = Order.objects.get(order_id=razorpay_order_id)
        except Order.DoesNotExist:
            return Response({'message': 'Order not found for given razorpay_order_id'}, status=status.HTTP_404_NOT_FOUND)

        # update order
        order.razorpay_payment_id = razorpay_payment_id
        order.razorpay_signature = razorpay_signature
        order.status = 'paid'
        order.attempts = order.attempts + 1
        order.save()

        # update user's subscription and plan info if applicable
        try:
            user = order.user
            plan = order.plan
            user.subscription_plan = plan
            if user.subscription_active:
                user.subscription_end_date = user.subscription_end_date + timedelta(days=plan.duration_days + 28*plan.duration_months + 365*plan.duration_years)
            else :
                user.subscription_start_date = date.today()
                user.subscription_end_date = user.subscription_start_date + timedelta(days=plan.duration_days + 28*plan.duration_months + 365*plan.duration_years)
                user.subscription_active = True
            if user.referral_code and not user.referral_code_used:
                user.referral_code_used = True
            user.save()
        except Exception as e:
            return Response({'message': 'Payment verified but failed to update user subscription'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'message': 'Payment verified and order updated', 'order_id': order.id}, status=status.HTTP_200_OK)


class PaymentHistoryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get(self, request):
        user = request.user
        orders = Order.objects.filter(user=user).order_by('-created_at').prefetch_related('plan')
        if not orders.exists():
            return Response({'message': 'No payment history found'}, status=status.HTTP_404_NOT_FOUND)

        client = _get_razorpay_client()
        data = []
        for o in orders:
            # refresh status in DB (will be a no-op for paid/expired orders)
            try:
                o = refresh_order_status(o, client=client, expire_after_hours=1)
            except Exception:
                # ensure we don't break history listing on unexpected errors
                pass

            data.append({
                'id': o.id,
                'order_id': o.order_id,
                'amount': o.amount,
                'status': o.status,
                'expired': o.expired,
                'currency': o.currency,
                'payment_id': o.razorpay_payment_id,
                'plan': PlanSerializer(o.plan).data,
                'created_at': o.created_at,
            })

        return Response({'message': 'Payment history retrieved successfully', 'history': data}, status=status.HTTP_200_OK)


class PaymentStatusView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        order = get_object_or_404(Order, id=id)
        # ensure user owns it
        if order.user != request.user:
            return Response({'message': 'Not authorized to view this payment'}, status=status.HTTP_403_FORBIDDEN)
        
        if order.expired:
            return Response({'message': 'This order has expired'}, status=status.HTTP_400_BAD_REQUEST)
        # attempt to refresh status (no-op for paid/expired orders)
        client = _get_razorpay_client()
        try:
            order = refresh_order_status(order, client=client, expire_after_hours=1)
        except Exception:
            # don't leak third-party errors to client
            pass

        if order.expired:
            return Response({'message': 'Order has expired'}, status=status.HTTP_400_BAD_REQUEST)

        data = {
            'id': order.id,
            'order_id': order.order_id,
            'status': order.status,
            'amount': order.amount,
            'currency': order.currency,
            'razorpay_order_id': order.razorpay_order_id,
            'razorpay_payment_id': order.razorpay_payment_id,
        }
        msg = 'Payment status retrieved' if order.status != 'paid' else 'Payment already completed'
        return Response({'message': msg, 'payment': data}, status=status.HTTP_200_OK)

class GetOrderView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, orderId):
        # orderId corresponds to our Order.order_id
        order = get_object_or_404(Order, order_id=orderId)
        if order.user != request.user:
            return Response({'message': 'Not authorized for this action'}, status=status.HTTP_403_FORBIDDEN)
        
        if order.expired:
            return Response({'message': 'The order is expired'}, status=status.HTTP_400_BAD_REQUEST)
        if datetime.now().astimezone() - order.created_at > timedelta(hours=1):
            order.expired = True
            order.save()
            return Response({'message': 'Order has expired, cannot make payment for this order'}, status=status.HTTP_400_BAD_REQUEST) 
        if order.status == 'paid':
            return Response({'message': 'Order is already paid'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'message': 'Order details fetched successfully',
            'order': {
                'id': order.id,
                'order_id': order.order_id,
                'amount': order.amount,
                'discount': order.plan.price - order.amount,
                'currency': order.currency,
                'plan' : PlanSerializer(order.plan).data,
                'name': order.plan.name,
                'key': _get_razorpay_client().auth[0],
                'description': order.plan.description,
            },
        }, status=status.HTTP_200_OK)
    
class CancelOrderView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, orderId):
        # orderId corresponds to our Order.order_id
        order = get_object_or_404(Order, order_id=orderId)
        if order.user != request.user:
            return Response({'message': 'Not authorized to cancel this order'}, status=status.HTTP_403_FORBIDDEN)
        
        if order.status == 'paid':
            return Response({'message': 'Cannot cancel a paid order'}, status=status.HTTP_400_BAD_REQUEST)
        
        order.expired = True
        order.save(update_fields=['expired'])
        return Response({'message': 'Order cancelled successfully'}, status=status.HTTP_200_OK)