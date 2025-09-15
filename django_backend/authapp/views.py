from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import SignupSerializer, VerifyOTPSerializer, LoginSerializer, UserSerializer
from .models import User, ReferralCode
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny
from django.middleware.csrf import get_token
from core.jwt_utils import generate_token_and_set_cookie
from core.email import sendOtpMail
from django.core.cache import cache
from core.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError



class SignupView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            if User.objects.filter(email=email.lower()).exists():
                return Response({'status': False, 'message': 'Email already registered.'}, status=status.HTTP_400_BAD_REQUEST)

            referral_code = serializer.validated_data.get('referral_code')
            if not (not referral_code or referral_code.strip() == "" or referral_code is None):   
                try: 
                    referral = ReferralCode.objects.get(code=referral_code)
                    if not referral.is_valid():
                        return Response({
                            'status': False,
                            'message': 'Invalid or expired referral code.'
                        }, status=status.HTTP_400_BAD_REQUEST)
                except ReferralCode.DoesNotExist:
                    return Response({
                        'status': False,
                        'message': 'Referral code not exists.'
                    }, status=status.HTTP_400_BAD_REQUEST)

            if sendOtpMail(email=email,action='signup', data = request.data) is False:
                return Response({'status': False, 'message': 'Failed to send OTP. Please try again later.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response({'status': True, 'message': 'OTP sent to email.'}, status=status.HTTP_200_OK)

        raise ValidationError(serializer.errors)

class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'status':False, 'message': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not User.objects.filter(email=email.lower()).exists():
            return Response({'status':False, 'message': 'User does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        if sendOtpMail(email, action='reset') is False:
            return Response({'status': False, 'message': 'Failed to send OTP. Please try again later.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        response =  Response({'status':True, 'message': 'OTP sent to email for password reset.'}, status=status.HTTP_200_OK)

        response.set_cookie(
            key="prc",
            value=email,
            max_age=180,
            httponly=True,
            secure=True,
            samesite='strict'
        )

        return response

class VerifyOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')

        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid() :
            email = serializer.validated_data.get('email')
            otp = serializer.validated_data.get('otp')

        if not otp:
            return Response({'status':False, 'message': 'OTP is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if len(str(otp)) != 6:
            return Response({'status':False, 'message': 'Invalid OTP.'}, status=status.HTTP_400_BAD_REQUEST)

        if not email or not otp:
            return Response({'status':False, 'message': 'Email and OTP are required.'}, status=status.HTTP_400_BAD_REQUEST)

        otp_data = cache.get(f"otp_{email}")

        if not otp_data or otp_data['otp'] != otp:
            return Response({'status':False, 'message': 'Invalid or expired OTP.'}, status=status.HTTP_400_BAD_REQUEST)

        action = otp_data['action']

        if action == 'signup':
            first_name = otp_data["data"].get('first_name')
            last_name = otp_data["data"].get('last_name')
            password = otp_data["data"].get('password')
            referral_code = otp_data["data"].get('referral_code')

            if User.objects.filter(email=email.lower()).exists():
                return Response({'status':False, 'message': 'User already exists.'}, status=status.HTTP_400_BAD_REQUEST)

            if referral_code:
                try:
                    referral = ReferralCode.objects.get(code=referral_code)
                    if not referral.is_valid():
                        return Response({
                            'status': False,
                            'message': 'Invalid or expired referral code.'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    referral.times_used += 1
                    referral.save()
                except ReferralCode.DoesNotExist:
                    return Response({
                        'status': False,
                        'message': 'Invalid referral code.'
                    }, status=status.HTTP_400_BAD_REQUEST)


            user = User.objects.create_user(
                email=email.lower(),
                password=password,
                first_name=first_name,
                last_name=last_name,
                verified=False,
                register_types=[],
                otp_verification=True,
                referral_code=referral if referral_code else None
            )
            cache.delete(f"otp_{email}")

            response = Response({'status':True, 'message': 'User registered successfully.', 'user': UserSerializer(user).data}, status=status.HTTP_201_CREATED)

            return generate_token_and_set_cookie(user=user, response=response)

        elif action == 'reset':
            response = Response({'status': True, 'message': 'otp verified successfully'}, status=status.HTTP_200_OK)
            response.set_cookie('prc', email, httponly=True, samesite='strict', max_age=600) 
            cache.delete(f"otp_{email}")
            return response

        else:
            return Response({'status':False, 'message': 'Invalid action type.'}, status=status.HTTP_400_BAD_REQUEST)

class UpdatePasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.COOKIES.get('prc')
        if not email:
            return Response({'message': 'Session expired or invalid, Please try again later.'}, status=status.HTTP_400_BAD_REQUEST)
        new_password = request.data.get('password')

        if not email or not new_password:
            return Response({'message': 'Email and new password are required.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'message': 'User does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        user.set_password(new_password)
        user.save()

        response = Response({'message': 'Password updated successfully. Try logging in with the new password.'}, status=status.HTTP_200_OK)
        response.delete_cookie('prc')
        cache.delete(f"otp_{email}")  

        return response

class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            user = authenticate(request, email=email.lower(), password=password)
            if user is None:
                return Response({'message': 'Invalid email or password.'}, status=status.HTTP_400_BAD_REQUEST)

            if not user.is_active:
                return Response({'message': 'Account is deactivated.'}, status=status.HTTP_403_FORBIDDEN)

            response = Response({'status':True, 'message': 'Login successful.', 'user': UserSerializer(user).data}, status=status.HTTP_200_OK)
            return generate_token_and_set_cookie(user=user, response=response)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        response = Response({
        'status': True,
        'message': 'Logout sucess.'
        }, status=status.HTTP_200_OK)
        response.delete_cookie('boj_token')
        return response


class AuthCheckView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = UserSerializer(request.user)
        print(type(user.data.get('first_opening_balance')))
        return Response({'status': True, 'user': user.data}, status=status.HTTP_200_OK)


class GetCSRFToken(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        # ensures the csrftoken cookie is set for the current session
        token = get_token(request)
        response = Response({'status': True, 'message': 'CSRF token set', 'csrftoken': token}, status=status.HTTP_200_OK)
        response.set_cookie('csrftoken', token)
        return response

