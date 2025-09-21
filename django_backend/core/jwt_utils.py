import jwt
import datetime
from django.conf import settings
from rest_framework.response import Response
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

JWT_SECRET = getattr(settings, 'JWT_SECRET')
JWT_ALGORITHM = getattr(settings, 'JWT_ALGORITHM')
JWT_EXP_DELTA_SECONDS = getattr(settings, 'JWT_EXP_DELTA_SECONDS')
JWT_COOKIE_NAME = 'boj_token'

def generate_token_and_set_cookie(user, response):
    payload = {
        'user_id': user.id,
        'email': user.email,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXP_DELTA_SECONDS)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    response.set_cookie(
        key=JWT_COOKIE_NAME,
        value=token,
        max_age=JWT_EXP_DELTA_SECONDS,
        httponly=True,
        secure=True,
        samesite='None'
    )

    return response


def extract_and_verify_token(request):
    token = None
    auth_header = request.headers.get('Authorization')


    if auth_header:
        try:
            prefix, token = auth_header.split(' ')
            if prefix.lower() != 'bearer':
                token = None
        except ValueError:
            token = None

    if not token:
        token = request.COOKIES.get(JWT_COOKIE_NAME)

    if not token:
        return None, _logout_response('Authentication credentials not provided. Log in again.')

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload, None
    except ExpiredSignatureError:
        return None, _logout_response('Session expired. Please log in again.')
    except InvalidTokenError:
        return None, _logout_response('Invalid token. Please log in again.')

def _logout_response(message):
    response = Response({
        'status': False,
        'message': message
    }, status=401)
    response.delete_cookie(JWT_COOKIE_NAME)
    return response
