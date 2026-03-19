"""
Development settings for django_backend project.
"""

from .base import *

print('loaded development settings')

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

SECRET_KEY = 'django-insecure-^04^4w_@m&cau1l(mbb^!i_dnt*hef+zaavaaj0+($(a-fmorz'

# CORS
CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173"
]

# CSRF
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173"
]
CSRF_COOKIE_SECURE = True  # Must be True for HTTPS in development
CSRF_COOKIE_SAMESITE = 'None'  # None allows cross-site requests
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript access

# Session
SESSION_COOKIE_SECURE = True  # Must be True for HTTPS in development
SESSION_COOKIE_SAMESITE = 'None'  # None allows cross-site requests

# Security Headers (relaxed for development)
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Database - PostgreSQL (local)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'bo_journal',
        'USER': 'postgres',
        'PASSWORD': 'secret',
        'HOST': 'localhost',
        'PORT': 5432,
    }
}

# Cache - Redis (local)
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT')
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_PASSWORD')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# JWT
JWT_SECRET = config('JWT_SECRET')
JWT_COOKIE_SECURE = True  # Must be True for HTTPS in development
JWT_COOKIE_SAMESITE = 'None'  # None allows cross-site requests

# S3
AWS_ACCESS_KEY_ID = config('S3_ACCESS_KEY')
AWS_SECRET_ACCESS_KEY = config('S3_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = config('S3_BUCKET_NAME')
AWS_S3_REGION_NAME = config('S3_REGION')
AWS_PRESIGNED_URL_EXPIRES = config('S3_PRESIGNED_URL_EXPIRES', default=600, cast=int)

# Celery
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/1'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/1'
CELERY_TIMEZONE = config("TIMEZONE", default="UTC")

# Timezone
TIME_ZONE = config("TIMEZONE", default="UTC")

# Razorpay
RAZORPAY_KEY = config('RAZORPAY_KEY')
RAZORPAY_SECRET = config('RAZORPAY_SECRET')

# Simple console logging for development
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}
