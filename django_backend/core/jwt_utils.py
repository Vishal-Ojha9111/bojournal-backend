import jwt
from jwt import PyJWTError, ExpiredSignatureError
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from rest_framework.response import Response
from typing import Dict, Optional, Tuple, Any
from django.contrib.auth.models import AbstractBaseUser
from rest_framework.request import Request

# Config - prefer explicit defaults and allow override in settings
JWT_SECRET = getattr(settings, 'JWT_SECRET', None)
JWT_ALGORITHM = getattr(settings, 'JWT_ALGORITHM', 'HS256')
JWT_EXP_DELTA_SECONDS = int(getattr(settings, 'JWT_EXP_DELTA_SECONDS', 60*60*24*3))  # 3 days
JWT_REFRESH_EXP_DELTA_SECONDS = int(getattr(settings, 'JWT_REFRESH_EXP_DELTA_SECONDS', 60*60*24*30))  # 30 days
JWT_COOKIE_NAME = getattr(settings, 'JWT_COOKIE_NAME', 'boj_token')
JWT_REFRESH_COOKIE_NAME = getattr(settings, 'JWT_REFRESH_COOKIE_NAME', 'boj_refresh_token')
JWT_COOKIE_SECURE = getattr(settings, 'JWT_COOKIE_SECURE', True)
JWT_COOKIE_SAMESITE = getattr(settings, 'JWT_COOKIE_SAMESITE', 'None')  # 'None' or 'Lax'/'Strict'

def _logout_response(message: str) -> Response:
    """Create a logout response with cleared cookies."""
    response = Response({'status': False, 'message': message}, status=401)
    response.delete_cookie(
        JWT_COOKIE_NAME,
        path='/',
        samesite=JWT_COOKIE_SAMESITE
    )
    response.delete_cookie(
        JWT_REFRESH_COOKIE_NAME,
        path='/',
        samesite=JWT_COOKIE_SAMESITE
    )
    return response

def generate_token_and_set_cookie(user: AbstractBaseUser, response: Response) -> Response:
    """
    Generate access token (3 days) and refresh token (30 days) and set them as cookies.
    
    Args:
        user: The user object to generate tokens for
        response: The Response object to set cookies on
        
    Returns:
        The modified Response object with cookies set
        
    Raises:
        RuntimeError: If JWT_SECRET is not configured
    """
    if not JWT_SECRET:
        raise RuntimeError('JWT_SECRET not configured')

    now = timezone.now()
    
    # Access token payload
    access_exp = now + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
    access_payload: Dict[str, Any] = {
        'user_id': user.id,
        'email': user.email,
        'iat': int(now.timestamp()),
        'exp': int(access_exp.timestamp()),
        'type': 'access'
    }
    
    # Refresh token payload
    refresh_exp = now + timedelta(seconds=JWT_REFRESH_EXP_DELTA_SECONDS)
    refresh_payload: Dict[str, Any] = {
        'user_id': user.id,
        'email': user.email,
        'iat': int(now.timestamp()),
        'exp': int(refresh_exp.timestamp()),
        'type': 'refresh'
    }

    # PyJWT >=2 returns str; older versions may return bytes
    access_token = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    refresh_token = jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    if isinstance(access_token, bytes):
        access_token = access_token.decode('utf-8')
    if isinstance(refresh_token, bytes):
        refresh_token = refresh_token.decode('utf-8')

    # Set access token cookie
    response.set_cookie(
        key=JWT_COOKIE_NAME,
        value=access_token,
        max_age=JWT_EXP_DELTA_SECONDS,
        httponly=True,
        secure=JWT_COOKIE_SECURE,
        samesite=JWT_COOKIE_SAMESITE,
    )
    
    # Set refresh token cookie
    response.set_cookie(
        key=JWT_REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=JWT_REFRESH_EXP_DELTA_SECONDS,
        httponly=True,
        secure=JWT_COOKIE_SECURE,
        samesite=JWT_COOKIE_SAMESITE,
    )
    
    return response

def extract_and_verify_token(request: Request) -> Tuple[Optional[Dict[str, Any]], Optional[Response]]:
    """
    Extract and verify JWT access token from request.
    Returns (payload, None) on success or (None, Response) on failure.
    Accepts Authorization: Bearer <token> or cookie JWT_COOKIE_NAME.
    Only accepts 'access' type tokens.
    
    Args:
        request: The HTTP request object
        
    Returns:
        Tuple of (payload dict, None) on success or (None, error Response) on failure
    """
    if not JWT_SECRET:
        # Fail fast with a sanitized message
        return None, _logout_response('Authentication not available (server misconfigured).')

    token: Optional[str] = None
    auth_header = request.headers.get('Authorization') or request.META.get('HTTP_AUTHORIZATION')

    if auth_header:
        # safer split: split at first whitespace
        parts = auth_header.split(None, 1)
        if len(parts) == 2 and parts[0].lower() == 'bearer':
            token = parts[1].strip()

    if not token:
        token = request.COOKIES.get(JWT_COOKIE_NAME)

    if not token:
        return None, _logout_response('Authentication credentials not provided. Log in again.')

    try:
        # decode with explicit algorithm list, returns dict payload
        payload: Dict[str, Any] = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except ExpiredSignatureError:
        return None, _logout_response('Session expired. Please log in again.')
    except PyJWTError:
        # covers InvalidTokenError, DecodeError, InvalidSignatureError etc.
        return None, _logout_response('Invalid token. Please log in again.')
    except Exception:
        # catch-all - sanitize
        return None, _logout_response('Authentication failed. Please log in again.')

    # Basic payload validation
    if not isinstance(payload, dict) or 'user_id' not in payload:
        return None, _logout_response('Invalid token payload. Please log in again.')
    
    # Ensure it's an access token
    if payload.get('type') != 'access':
        return None, _logout_response('Invalid token type. Please log in again.')

    # optionally: enforce token issued-at and expiry checks or leeway
    return payload, None


def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a refresh token.
    
    Args:
        token: The JWT refresh token string to verify
        
    Returns:
        Payload dict on success or None on failure
    """
    if not JWT_SECRET:
        return None

    try:
        payload: Dict[str, Any] = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # Basic validation
        if not isinstance(payload, dict) or 'user_id' not in payload:
            return None
        
        # Ensure it's a refresh token
        if payload.get('type') != 'refresh':
            return None
            
        return payload
    except (ExpiredSignatureError, PyJWTError, Exception):
        return None
