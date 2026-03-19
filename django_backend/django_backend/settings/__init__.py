"""
Settings module initialization.
Loads appropriate settings based on DJANGO_ENVIRONMENT variable.
"""

import os
from decouple import config

# Determine environment
ENVIRONMENT = config('DJANGO_ENVIRONMENT', default='development')

print(f"Loading Django settings for environment: {ENVIRONMENT}")

if ENVIRONMENT == 'production':
    from .production import *
    print("✓ Production settings loaded")
elif ENVIRONMENT == 'testing':
    from .testing import *
    print("✓ Testing settings loaded")
else:
    from .development import *
    print("✓ Development settings loaded")
