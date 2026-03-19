"""
Custom throttling classes for rate limiting API requests.
"""
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class AuthenticatedUserRateThrottle(UserRateThrottle):
    """
    Rate limit for authenticated users: 100 requests per minute.
    Admins (is_staff=True) are exempt from throttling.
    """
    scope = 'authenticated_user'
    
    def allow_request(self, request, view):
        # Exempt admin users from throttling
        if request.user and request.user.is_authenticated and request.user.is_staff:
            return True
        return super().allow_request(request, view)


class AnonymousUserRateThrottle(AnonRateThrottle):
    """
    Rate limit for anonymous users: 100 requests per minute.
    """
    scope = 'anonymous_user'


class AuthEndpointThrottle(AnonRateThrottle):
    """
    Stricter rate limit for authentication endpoints: 20 requests per minute.
    Helps prevent brute force attacks on login/signup/OTP verification.
    """
    scope = 'auth_endpoint'
