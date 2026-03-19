from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import SignupSerializer, VerifyOTPSerializer, LoginSerializer, UserSerializer
from .models import User, ReferralCode
from .models import SignupPending
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny
from django.middleware.csrf import get_token
from core.jwt_utils import generate_token_and_set_cookie, verify_refresh_token
from emailservice.dispatcher import enqueue_email
from django.core.cache import cache
from core.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import JSONParser
from core.s3_utils import generate_presigned_view_url
from django.conf import settings
from core.throttling import AuthEndpointThrottle
import logging
from django.core import signing
from django.core.signing import BadSignature, SignatureExpired


class SignupView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # Public endpoint
    throttle_classes = [AuthEndpointThrottle]
    
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

            # create pending signup record and send otp without caching plaintext password
            first_name = serializer.validated_data.get('first_name')
            last_name = serializer.validated_data.get('last_name')
            password = serializer.validated_data.get('password')
            referral_code = serializer.validated_data.get('referral_code')
            pending = SignupPending.create_pending(email=email, first_name=first_name, last_name=last_name, raw_password=password, referral_code=referral_code)
            
            # Store OTP in cache for verification (same as old sendOtpMail behavior)
            cache_data = {'action': 'signup', 'otp': pending.otp, 'pending_id': pending.id}
            cache.set(f"otp_{email.lower()}", cache_data, timeout=300)
            
            # Send OTP email via new email service with critical priority
            try:
                enqueue_email(
                    key='otp',
                    to_email=email.lower(),
                    data={'otp': pending.otp, 'app_name': 'BO Journal'},
                    priority='critical',
                    locale='en'
                )
            except Exception as e:
                pending.delete()
                cache.delete(f"otp_{email.lower()}")
                return Response({'status': False, 'message': 'Failed to send OTP. Please try again later.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({'status': True, 'message': 'OTP sent to email.'}, status=status.HTTP_200_OK)

        raise ValidationError(serializer.errors)

class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # Public endpoint
    throttle_classes = [AuthEndpointThrottle]
    
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'status':False, 'message': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not User.objects.filter(email=email.lower()).exists():
            return Response({'status':False, 'message': 'User does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        # Generate OTP and store in cache for verification
        import random
        otp = str(random.randint(100000, 999999))
        cache_data = {'action': 'reset', 'otp': otp}
        cache.set(f"otp_{email.lower()}", cache_data, timeout=300)
        
        # Send OTP email via new email service with critical priority
        try:
            enqueue_email(
                key='otp',
                to_email=email.lower(),
                data={'otp': otp, 'app_name': 'BO Journal'},
                priority='critical',
                locale='en'
            )
        except Exception as e:
            cache.delete(f"otp_{email.lower()}")
            return Response({'status': False, 'message': 'Failed to send OTP. Please try again later.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # sign email instead of storing plaintext to prevent forgery
        signed_email = signing.dumps(email.lower())

        response =  Response({'status':True, 'message': 'OTP sent to email for password reset.'}, status=status.HTTP_200_OK)

        response.set_cookie(
            key="prc",
            value=signed_email,
            max_age=180,
            httponly=True,
            secure=settings.CSRF_COOKIE_SECURE,  # Use environment setting
            samesite=settings.CSRF_COOKIE_SAMESITE  # Use environment setting
        )

        return response

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # Public endpoint
    throttle_classes = [AuthEndpointThrottle]
    
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

        # Check OTP attempt count
        attempts_key = f"otp_attempts_{email.lower()}"
        attempts = cache.get(attempts_key, 0)
        
        # Maximum 10 attempts
        if attempts >= 10:
            # Expire the OTP
            cache.delete(f"otp_{email.lower()}")
            cache.delete(attempts_key)
            return Response({
                'status': False, 
                'message': 'OTP expired due to maximum attempts exceeded. Please request a new OTP.'
            }, status=status.HTTP_400_BAD_REQUEST)

        otp_data = cache.get(f"otp_{email.lower()}")

        if not otp_data or otp_data['otp'] != otp:
            # Increment attempt count
            attempts += 1
            cache.set(attempts_key, attempts, timeout=600)  # 10 minutes timeout
            
            # Calculate backoff time (exponential: 2^attempts seconds)
            backoff_time = min(2 ** attempts, 300)  # Max 300 seconds (5 minutes)
            
            remaining_attempts = 10 - attempts
            if remaining_attempts > 0:
                return Response({
                    'status': False, 
                    'message': f'Invalid or expired OTP. {remaining_attempts} attempts remaining. Please wait {backoff_time} seconds before next attempt.'
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Expire the OTP after max attempts
                cache.delete(f"otp_{email.lower()}")
                cache.delete(attempts_key)
                return Response({
                    'status': False, 
                    'message': 'OTP expired due to maximum attempts exceeded. Please request a new OTP.'
                }, status=status.HTTP_400_BAD_REQUEST)

        # Clear attempts on successful verification
        cache.delete(attempts_key)
        
        action = otp_data['action']

        if action == 'signup':
            # Use SignupPending record to create user
            pending_id = otp_data.get('pending_id')
            pending = None
            if pending_id:
                try:
                    pending = SignupPending.objects.get(id=pending_id, email=email.lower())
                except SignupPending.DoesNotExist:
                    pending = None

            if not pending or pending.is_expired():
                return Response({'status': False, 'message': 'Signup session expired. Please signup again.'}, status=status.HTTP_400_BAD_REQUEST)

            referral_code = pending.referral_code
            if User.objects.filter(email=email.lower()).exists():
                pending.delete()
                return Response({'status':False, 'message': 'User already exists.'}, status=status.HTTP_400_BAD_REQUEST)
            if referral_code:
                try:
                    referral = ReferralCode.objects.get(code=referral_code)
                    if not referral.is_valid():
                        return Response({'status': False, 'message': 'Invalid or expired referral code.'}, status=status.HTTP_400_BAD_REQUEST)
                    referral.times_used += 1
                    referral.save()
                except ReferralCode.DoesNotExist:
                    return Response({'status': False, 'message': 'Invalid referral code.'}, status=status.HTTP_400_BAD_REQUEST)


            # create user using the hashed password from pending
            user = User.objects.create_user(
                email=email.lower(),
                password=None,
                first_name=pending.first_name,
                last_name=pending.last_name,
                otp_verification=True,
                referral_code=referral if referral_code else None
            )
            # set the password from the pending hashed value
            user.password = pending.password_hash
            user.save()
            pending.delete()
            cache.delete(f"otp_{email.lower()}")
            
            # Send welcome email (low priority, non-blocking)
            try:
                enqueue_email(
                    key='welcome',
                    to_email=user.email,
                    data={
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'app_name': 'BO Journal'
                    },
                    priority='low',  # Lowest priority - user doesn't need this immediately
                    locale='en'
                )
            except Exception as e:
                # Log but don't block signup if welcome email fails
                import logging
                logger = logging.getLogger(__name__)
                logger.exception(f"Failed to send welcome email to {user.email}: {e}")

            response = Response({'status':True, 'message': 'User registered successfully.', 'user': UserSerializer(user).data}, status=status.HTTP_201_CREATED)
            return generate_token_and_set_cookie(user=user, response=response)

        elif action == 'reset':
            # set a signed, time-limited cookie (longer than initial OTP stage) so UpdatePasswordView can trust it
            signed_email = signing.dumps(email.lower())
            response = Response({'status': True, 'message': 'otp verified successfully'}, status=status.HTTP_200_OK)
            response.set_cookie(
                'prc', 
                signed_email, 
                httponly=True, 
                secure=settings.CSRF_COOKIE_SECURE,  # Use environment setting
                samesite=settings.CSRF_COOKIE_SAMESITE,  # Use environment setting
                max_age=600
            )
            cache.delete(f"otp_{email.lower()}")
            return response

        else:
            return Response({'status':False, 'message': 'Invalid action type.'}, status=status.HTTP_400_BAD_REQUEST)

class UpdatePasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # Public endpoint

    def post(self, request):
        signed_email = request.COOKIES.get('prc')
        if not signed_email:
            return Response({'message': 'Session expired or invalid, Please try again later.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # validate signature and timestamp (max_age should match the value set in VerifyOTPView)
            email = signing.loads(signed_email, max_age=600)
        except SignatureExpired:
            return Response({'message': 'Session expired or invalid, Please try again later.'}, status=status.HTTP_400_BAD_REQUEST)
        except BadSignature:
            return Response({'message': 'Session invalid, Please try again later.'}, status=status.HTTP_400_BAD_REQUEST)

        new_password = request.data.get('password')

        if not email or not new_password:
            return Response({'message': 'Email and new password are required.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email.lower())
        except User.DoesNotExist:
            return Response({'message': 'User does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        user.set_password(new_password)
        user.save()

        response = Response({'message': 'Password updated successfully. Try logging in with the new password.'}, status=status.HTTP_200_OK)
        response.delete_cookie('prc', path='/', samesite=settings.CSRF_COOKIE_SAMESITE)
        cache.delete(f"otp_{email}")  

        return response

class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # Public endpoint
    throttle_classes = [AuthEndpointThrottle]
    
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
    authentication_classes = []  # Public endpoint (clears cookies)
    
    def get(self, request):
        response = Response({
        'status': True,
        'message': 'Logout sucess.'
        }, status=status.HTTP_200_OK)
        response.delete_cookie(
            'boj_token',
            path='/',
            samesite=settings.SESSION_COOKIE_SAMESITE
        )
        response.delete_cookie(
            'boj_refresh_token',
            path='/',
            samesite=settings.SESSION_COOKIE_SAMESITE
        )
        return response


class RefreshTokenView(APIView):
    """
    Refresh access token using refresh token.
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # Public endpoint (uses refresh token)
    throttle_classes = [AuthEndpointThrottle]
    
    def post(self, request):
        refresh_token = request.COOKIES.get('boj_refresh_token')
        
        if not refresh_token:
            return Response({
                'status': False,
                'message': 'Refresh token not found. Please log in again.'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        payload = verify_refresh_token(refresh_token)
        
        if not payload:
            response = Response({
                'status': False,
                'message': 'Invalid or expired refresh token. Please log in again.'
            }, status=status.HTTP_401_UNAUTHORIZED)
            response.delete_cookie('boj_token', path='/', samesite=settings.SESSION_COOKIE_SAMESITE)
            response.delete_cookie('boj_refresh_token', path='/', samesite=settings.SESSION_COOKIE_SAMESITE)
            return response
        
        # Get user from payload
        try:
            user = User.objects.get(id=payload['user_id'])
        except User.DoesNotExist:
            return Response({
                'status': False,
                'message': 'User not found. Please log in again.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if not user.is_active:
            return Response({
                'status': False,
                'message': 'Account is deactivated.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generate new tokens
        response = Response({
            'status': True,
            'message': 'Token refreshed successfully.',
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)
        
        return generate_token_and_set_cookie(user=user, response=response)


class AuthCheckView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = UserSerializer(request.user)
        return Response({'status': True, 'user': user.data}, status=status.HTTP_200_OK)


class UpdateUserView(APIView):
    """Authenticated view to update allowed user fields."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def patch(self, request):
        user = request.user
        data = request.data or {}

        # Only allow updating these user-controlled fields from this endpoint
        allowed = {'first_name', 'last_name', 'profile_picture_key'}
        forbidden_attempts = [k for k in data.keys() if k not in allowed]
        if forbidden_attempts:
            # Explicitly reject attempts to modify forbidden fields (e.g., subscription fields)
            return Response({'status': False, 'message': 'Attempted to update forbidden fields.', 'forbidden_fields': forbidden_attempts}, status=status.HTTP_400_BAD_REQUEST)

        updated = False
        for key, val in data.items():
            if key in allowed:
                setattr(user, key, val)
                updated = True

        if updated:
            user.save()
            return Response({'status': True, 'message': 'User updated.', 'user': UserSerializer(user).data}, status=status.HTTP_200_OK)

        return Response({'status': False, 'message': 'No valid fields to update.'}, status=status.HTTP_400_BAD_REQUEST)


class ProfilePictureURLView(APIView):
    """Return presigned GET URL for the authenticated user's profile picture."""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        key = getattr(user, 'profile_picture_key', None)
        if not key:
            return Response({'status': False, 'message': 'Invalid image key.'}, status=status.HTTP_400_BAD_REQUEST)

        # support dict stored keys
        if isinstance(key, dict):
            possible = [key.get('key'), key.get('s3_key'), key.get('object_key')]
            key = next((p for p in possible if p), None)

        if not key:
            return Response({'status': False, 'message': 'Invalid profile picture key.'}, status=status.HTTP_400_BAD_REQUEST)

        expires = getattr(settings, 'PROFILE_PICTURE_URL_EXPIRES', None)
        if expires is None:
            expires = getattr(settings, 'AWS_PRESIGNED_URL_EXPIRES', 600)

        try:
            url = generate_presigned_view_url(key=key, expires_in=int(expires))
            return Response({'status': True, 'url': url, 'expires_in': int(expires)}, status=status.HTTP_200_OK)
        except Exception as e:
            logging.exception('Failed to generate presigned URL for user %s: %s', getattr(user, 'email', '<unknown>'), e)
            return Response({'status': False, 'message': 'Failed to generate URL.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetCSRFToken(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # Explicitly disable authentication
    
    def get(self, request):
        # ensures the csrftoken cookie is set for the current session
        token = get_token(request)
        response = Response({
            'status': True,
            'message': 'CSRF token set',
            'csrftoken': token
        }, status=status.HTTP_200_OK)
        
        # Set cookie with environment-appropriate settings
        print(settings.CSRF_COOKIE_SECURE, settings.CSRF_COOKIE_SAMESITE)
        response.set_cookie(
            key='csrftoken',
            value=token,
            max_age=31449600,  # 1 year
            secure=settings.CSRF_COOKIE_SECURE,  # Use environment setting
            httponly=False,  # Allow JavaScript access
            samesite=settings.CSRF_COOKIE_SAMESITE,  # Use environment setting
            path='/',
        )
        return response


class HealthCheckView(APIView):
    """
    Health check endpoint for monitoring system status.
    Returns status of database, Redis cache, and Celery workers.
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # Public health check endpoint
    
    def get(self, request):
        from django.db import connection
        from django.utils import timezone
        
        health_status = {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'checks': {}
        }
        
        # Database health check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            health_status['checks']['database'] = {
                'status': 'healthy',
                'message': 'Database connection successful'
            }
        except Exception as e:
            health_status['checks']['database'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['status'] = 'unhealthy'
        
        # Redis cache health check
        try:
            cache.set('health_check_test', 'ok', 10)
            result = cache.get('health_check_test')
            if result == 'ok':
                health_status['checks']['redis'] = {
                    'status': 'healthy',
                    'message': 'Redis cache operational'
                }
            else:
                health_status['checks']['redis'] = {
                    'status': 'degraded',
                    'message': 'Redis read/write issue'
                }
                health_status['status'] = 'degraded'
        except Exception as e:
            health_status['checks']['redis'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            if health_status['status'] == 'healthy':
                health_status['status'] = 'degraded'
        
        # Celery worker health check
        try:
            from celery import current_app
            inspector = current_app.control.inspect()
            stats = inspector.stats()
            
            if stats:
                active_workers = len(stats)
                health_status['checks']['celery'] = {
                    'status': 'healthy',
                    'workers': active_workers,
                    'message': f'{active_workers} worker(s) active'
                }
            else:
                health_status['checks']['celery'] = {
                    'status': 'unhealthy',
                    'workers': 0,
                    'message': 'No Celery workers available'
                }
                if health_status['status'] == 'healthy':
                    health_status['status'] = 'degraded'
        except Exception as e:
            health_status['checks']['celery'] = {
                'status': 'unknown',
                'error': str(e),
                'message': 'Unable to check Celery status'
            }
        
        # Determine HTTP status code
        status_code = status.HTTP_200_OK if health_status['status'] == 'healthy' else status.HTTP_503_SERVICE_UNAVAILABLE
        
        return Response(health_status, status=status_code)
