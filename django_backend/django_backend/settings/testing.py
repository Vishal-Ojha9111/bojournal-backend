"""
Testing settings for django_backend project.
"""

from .base import *

print('loaded testing settings')

DEBUG = True
SECRET_KEY = 'test-secret-key-not-for-production'

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']

# Use SQLite for testing (faster)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db_test.sqlite3',
    }
}

# Disable cache for consistent test results
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Use console email backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable Celery in tests (run tasks synchronously)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'

# JWT test config
JWT_SECRET = 'test-jwt-secret'
JWT_COOKIE_SECURE = False
JWT_COOKIE_SAMESITE = 'Lax'  # Lax for testing

# CSRF for testing
CSRF_COOKIE_SECURE = False  # Must be False for HTTP testing
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False

# Session for testing
SESSION_COOKIE_SECURE = False  # Must be False for HTTP testing
SESSION_COOKIE_SAMESITE = 'Lax'

# Disable throttling for tests
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}

# Simple test logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
}

# S3 - use mock or skip
AWS_ACCESS_KEY_ID = 'test-access-key'
AWS_SECRET_ACCESS_KEY = 'test-secret-key'
AWS_STORAGE_BUCKET_NAME = 'test-bucket'
AWS_S3_REGION_NAME = 'us-east-1'

# Razorpay test keys
RAZORPAY_KEY = 'test-razorpay-key'
RAZORPAY_SECRET = 'test-razorpay-secret'

# Timezone
TIME_ZONE = 'UTC'
CELERY_TIMEZONE = 'UTC'
