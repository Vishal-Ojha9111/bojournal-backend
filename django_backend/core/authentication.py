import logging
from typing import Optional, Tuple, Any, Dict
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
from core.jwt_utils import extract_and_verify_token
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)
User = get_user_model()

class JWTAuthentication(BaseAuthentication):
    """
    Authenticate requests using a JWT-like helper `extract_and_verify_token`.
    Returns (user, auth) on success, raises AuthenticationFailed on failure.
    """

    def authenticate(self, request: Request) -> Optional[Tuple[AbstractBaseUser, Dict[str, Any]]]:
        """
        Authenticate the request using JWT token.
        
        Args:
            request: The HTTP request object
            
        Returns:
            Tuple of (user, payload) on success or None if no authentication attempted
            
        Raises:
            AuthenticationFailed: If authentication fails
        """
        payload, error_response = extract_and_verify_token(request)

        # If token helper returned an error response, extract safe message and fail
        if error_response:
            # Try structured message first, fall back to textual representation
            msg: Optional[str] = None
            try:
                data = getattr(error_response, 'data', None)
                if isinstance(data, dict):
                    msg = data.get('message') or data.get('detail')
                elif data:
                    msg = str(data)
            except Exception:
                msg = None

            safe_msg = msg or _('Authentication failed')
            # Log for observability (do not log token contents)
            logger.info("Authentication failed: %s (remote=%s)", safe_msg, request.META.get('REMOTE_ADDR'))
            raise AuthenticationFailed(safe_msg)

        # Validate payload shape
        if not payload or not isinstance(payload, dict) or 'user_id' not in payload:
            logger.info("Authentication failed: invalid token payload (remote=%s)", request.META.get('REMOTE_ADDR'))
            raise AuthenticationFailed(_('Invalid authentication token'))

        user_id = payload['user_id']
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            logger.info("Authentication failed: user not found (user_id=%s remote=%s)", user_id, request.META.get('REMOTE_ADDR'))
            raise AuthenticationFailed(_('User not found. Please log in again.'))

        # Optional: reject inactive users
        if getattr(user, 'is_active', True) is False:
            logger.info("Authentication failed: inactive account (user_id=%s)", user_id)
            raise AuthenticationFailed(_('Account is inactive.'))

        # return the user and token payload as the auth object for later use if needed
        return (user, payload)
