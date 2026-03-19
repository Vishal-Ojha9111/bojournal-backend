"""
Production settings for django_backend project.
"""

from .base import *
import os

print('loaded production settings')

DEBUG = False

SECRET_KEY = config('SECRET_KEY')

ALLOWED_HOSTS = [config('HOST0')]

# CORS
CORS_ALLOWED_ORIGINS = [
    config('ORIGIN0'),
    config('ORIGIN1')
]

# CSRF
CSRF_TRUSTED_ORIGINS = [
    config('ORIGIN0'),
    config('ORIGIN1')
]
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_HTTPONLY = True

# Security Headers (strict)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'None'

# Database connection pooling - 10 minutes for production
CONN_MAX_AGE = 600

# Static files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Database - PostgreSQL with connection pooling
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
        'CONN_MAX_AGE': 600,  # Connection pooling: 10 minutes
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'  # 30 seconds query timeout
        }
    }
}

# Cache - Redis (production)
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config('REDIS_LOCATION'),
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
JWT_COOKIE_SECURE = True
JWT_COOKIE_SAMESITE = 'None'

# S3
AWS_ACCESS_KEY_ID = config('S3_ACCESS_KEY')
AWS_SECRET_ACCESS_KEY = config('S3_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = config('S3_BUCKET_NAME')
AWS_S3_REGION_NAME = config('S3_REGION')
AWS_PRESIGNED_URL_EXPIRES = config('S3_PRESIGNED_URL_EXPIRES', default=600, cast=int)

# Celery
CELERY_BROKER_URL = config('REDIS_LOCATION')
CELERY_RESULT_BACKEND = config('REDIS_LOCATION')
CELERY_TIMEZONE = config("TIMEZONE")

# Timezone
TIME_ZONE = config("TIMEZONE")

# Razorpay
RAZORPAY_KEY = config('RAZORPAY_KEY')
RAZORPAY_SECRET = config('RAZORPAY_SECRET')

# JSON Logging for production
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d %(funcName)s'
        },
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'app.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'authapp': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'journal': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'transactions': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)
