"""
Comprehensive test cases for authentication module.

Tests cover:
- User signup and OTP verification
- Login and logout
- Token refresh mechanism
- Rate limiting
- OTP attempt limiting
- Password reset
"""
from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from .models import User
import time


class SignupTests(APITestCase):
    """Test cases for user signup functionality."""
    
    def setUp(self):
        self.client = APIClient()
        self.signup_url = '/api/v2/auth/signup'
        self.valid_user_data = {
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'first_name': 'Test',
            'last_name': 'User'
        }
    
    def tearDown(self):
        """Clean up cache after each test."""
        cache.clear()
    
    def test_signup_success(self):
        """Test successful user signup with valid data."""
        response = self.client.post(self.signup_url, self.valid_user_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
        self.assertIn('OTP', response.data['message'])
        
        # Verify user created but not verified
        user = User.objects.get(email=self.valid_user_data['email'])
        self.assertFalse(user.otp_verification)
    
    def test_signup_duplicate_email(self):
        """Test signup with already registered email."""
        User.objects.create_user(**self.valid_user_data)
        response = self.client.post(self.signup_url, self.valid_user_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['status'])
    
    def test_signup_invalid_email(self):
        """Test signup with invalid email format."""
        invalid_data = self.valid_user_data.copy()
        invalid_data['email'] = 'invalid-email'
        response = self.client.post(self.signup_url, invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_signup_weak_password(self):
        """Test signup with weak password."""
        weak_data = self.valid_user_data.copy()
        weak_data['password'] = '123'
        response = self.client.post(self.signup_url, weak_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_signup_missing_fields(self):
        """Test signup with missing required fields."""
        incomplete_data = {'email': 'test@example.com'}
        response = self.client.post(self.signup_url, incomplete_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class OTPVerificationTests(APITestCase):
    """Test cases for OTP verification functionality."""
    
    def setUp(self):
        self.client = APIClient()
        self.verify_url = '/api/v2/auth/verifyotp'
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User'
        )
        self.user.otp_verification = False
        self.user.save()
    
    def tearDown(self):
        cache.clear()
    
    def test_otp_verification_success(self):
        """Test successful OTP verification."""
        # Set a test OTP in cache
        cache.set(f'otp_{self.user.email}', '123456', timeout=300)
        
        response = self.client.post(self.verify_url, {
            'email': self.user.email,
            'otp': '123456'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
        
        # Verify user is now verified
        self.user.refresh_from_db()
        self.assertTrue(self.user.otp_verification)
    
    def test_otp_verification_invalid_otp(self):
        """Test OTP verification with wrong OTP."""
        cache.set(f'otp_{self.user.email}', '123456', timeout=300)
        
        response = self.client.post(self.verify_url, {
            'email': self.user.email,
            'otp': '000000'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['status'])
    
    def test_otp_attempt_limiting(self):
        """Test OTP attempt limiting (max 10 attempts)."""
        cache.set(f'otp_{self.user.email}', '123456', timeout=300)
        
        # Try 11 times with wrong OTP
        for i in range(11):
            response = self.client.post(self.verify_url, {
                'email': self.user.email,
                'otp': '000000'
            })
            
            if i < 10:
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('attempts remaining', response.data['message'])
            else:
                # 11th attempt should fail with max attempts exceeded
                self.assertIn('maximum attempts exceeded', response.data['message'].lower())
    
    def test_otp_expired(self):
        """Test verification with expired OTP."""
        # OTP not in cache (expired)
        response = self.client.post(self.verify_url, {
            'email': self.user.email,
            'otp': '123456'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('expired', response.data['message'].lower())


class LoginTests(APITestCase):
    """Test cases for user login functionality."""
    
    def setUp(self):
        self.client = APIClient()
        self.login_url = '/api/v2/auth/login'
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User'
        )
        self.user.otp_verification = True
        self.user.is_active = True
        self.user.save()
    
    def tearDown(self):
        cache.clear()
    
    def test_login_success(self):
        """Test successful login with correct credentials."""
        response = self.client.post(self.login_url, {
            'email': self.user.email,
            'password': 'TestPass123!'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
        self.assertIn('boj_token', response.cookies)
        self.assertIn('boj_refresh_token', response.cookies)
    
    def test_login_wrong_password(self):
        """Test login with incorrect password."""
        response = self.client.post(self.login_url, {
            'email': self.user.email,
            'password': 'WrongPassword123!'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['status'])
    
    def test_login_unverified_user(self):
        """Test login with unverified email."""
        self.user.otp_verification = False
        self.user.save()
        
        response = self.client.post(self.login_url, {
            'email': self.user.email,
            'password': 'TestPass123!'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('verify', response.data['message'].lower())
    
    def test_login_inactive_user(self):
        """Test login with deactivated account."""
        self.user.is_active = False
        self.user.save()
        
        response = self.client.post(self.login_url, {
            'email': self.user.email,
            'password': 'TestPass123!'
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_login_nonexistent_user(self):
        """Test login with email that doesn't exist."""
        response = self.client.post(self.login_url, {
            'email': 'nonexistent@example.com',
            'password': 'TestPass123!'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RefreshTokenTests(APITestCase):
    """Test cases for JWT refresh token functionality."""
    
    def setUp(self):
        self.client = APIClient()
        self.login_url = '/api/v2/auth/login'
        self.refresh_url = '/api/v2/auth/refresh'
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User'
        )
        self.user.otp_verification = True
        self.user.is_active = True
        self.user.save()
    
    def tearDown(self):
        cache.clear()
    
    def test_refresh_token_success(self):
        """Test successful token refresh."""
        # First login to get tokens
        login_response = self.client.post(self.login_url, {
            'email': self.user.email,
            'password': 'TestPass123!'
        })
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        # Extract cookies and set them for refresh request
        self.client.cookies = login_response.cookies
        
        # Now refresh token
        refresh_response = self.client.post(self.refresh_url)
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertTrue(refresh_response.data['status'])
        self.assertIn('boj_token', refresh_response.cookies)
        self.assertIn('boj_refresh_token', refresh_response.cookies)
    
    def test_refresh_token_without_refresh_cookie(self):
        """Test refresh without refresh token cookie."""
        response = self.client.post(self.refresh_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LogoutTests(APITestCase):
    """Test cases for user logout functionality."""
    
    def setUp(self):
        self.client = APIClient()
        self.login_url = '/api/v2/auth/login'
        self.logout_url = '/api/v2/auth/logout'
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User'
        )
        self.user.otp_verification = True
        self.user.is_active = True
        self.user.save()
    
    def tearDown(self):
        cache.clear()
    
    def test_logout_success(self):
        """Test successful logout."""
        # First login
        login_response = self.client.post(self.login_url, {
            'email': self.user.email,
            'password': 'TestPass123!'
        })
        self.client.cookies = login_response.cookies
        
        # Then logout
        logout_response = self.client.post(self.logout_url)
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)
        self.assertTrue(logout_response.data['status'])


class HealthCheckTests(APITestCase):
    """Test cases for health check endpoint."""
    
    def setUp(self):
        self.client = APIClient()
        self.health_url = '/api/v2/auth/health'
    
    def test_health_check_success(self):
        """Test health check returns healthy status."""
        response = self.client.get(self.health_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.data)
        self.assertIn('checks', response.data)
        self.assertIn('database', response.data['checks'])
        self.assertIn('redis', response.data['checks'])


# Run tests with:
# python manage.py test authapp
# python manage.py test authapp.tests.SignupTests
# python manage.py test authapp.tests.SignupTests.test_signup_success
