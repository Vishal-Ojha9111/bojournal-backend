from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from core.jwt_utils import extract_and_verify_token
from authapp.models import User

class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        payload, error_response = extract_and_verify_token(request)

        if error_response:
            raise AuthenticationFailed(error_response.data.get('Authentication failed'))

        try:
            user = User.objects.get(id=payload['user_id'])
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found. Please log in again.')

        return (user, None)
