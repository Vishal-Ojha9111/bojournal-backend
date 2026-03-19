"""
Base settings for django_backend project.
Common settings shared across all environments.
"""

from pathlib import Path
from decouple import config
from dotenv import load_dotenv
from celery.schedules import crontab
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv()

print('loaded base settings')

# CORS
CORS_ALLOW_CREDENTIALS = True

# Application definition
INSTALLED_APPS = [
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'authapp',
    'transactions',
    'journal',
    'holiday',
    'registers',
    'payment',
    'emailservice'
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
]

ROOT_URLCONF = 'django_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'django_backend.wsgi.application'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'authapp.User'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'core.authentication.JWTAuthentication'
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated'
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'EXCEPTION_HANDLER': 'core.exception_handler.custom_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [
        'core.throttling.AuthenticatedUserRateThrottle',
        'core.throttling.AnonymousUserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'authenticated_user': '100/minute',
        'anonymous_user': '100/minute',
        'auth_endpoint': '20/minute',
    }
}

ALLOWED_IMAGE_KEYS = ['profile_pictures/', 'transactions/']

# JWT Configuration (common)
JWT_ALGORITHM = 'HS256'
JWT_EXP_DELTA_SECONDS = 60*60*24*3  # 3 days
JWT_REFRESH_EXP_DELTA_SECONDS = 60*60*24*30  # 30 days
JWT_COOKIE_NAME = 'boj_token'
JWT_REFRESH_COOKIE_NAME = 'boj_refresh_token'

# Celery Configuration (common)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# Email Priority Queues Configuration
CELERY_TASK_ROUTES = {
    'emailservice.tasks.send_email_task': {
        'queue': 'default',
    },
}

CELERY_TASK_QUEUE_MAX_PRIORITY = 10
CELERY_TASK_DEFAULT_PRIORITY = 5

CELERY_BROKER_TRANSPORT_OPTIONS = {
    'priority_steps': list(range(11)),
    'queue_order_strategy': 'priority',
}

CELERY_BEAT_SCHEDULE = {
    "create-daily-journals": {
        "task": "journal.tasks.create_daily_journals",
        "schedule": crontab(minute=0, hour=0),
    },
    "update-subscriptions": {
        "task": "payment.tasks.update_subscription",
        "schedule": crontab(minute=0, hour=0),
    },
}
