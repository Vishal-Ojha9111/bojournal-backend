# Django Settings Usage Guide

## Overview

The Django backend uses a modular settings structure with three environments:
- **Development** - Local development with debugging enabled
- **Testing** - Optimized for running tests
- **Production** - Production-ready with security hardening

## How Settings Are Loaded

The settings loader (`django_backend/settings/__init__.py`) uses the following priority:

1. **Environment Variable** (highest priority)
2. **.env file** (fallback)
3. **Default** ('development' if nothing is set)

## ⚠️ Important: Environment Variable Priority

**The `decouple` library prioritizes environment variables over `.env` file values.**

This means:
- If you set `export DJANGO_ENVIRONMENT=testing` in your terminal, it will **override** the value in `.env`
- The terminal environment variable persists until you close the terminal or unset it
- This can cause confusion when the wrong environment loads

## How to Use Each Environment

### 1. Development Environment (Default)

**Method 1: Using .env file (Recommended)**
```bash
# Set in your .env file
DJANGO_ENVIRONMENT=development

# Make sure no terminal environment variable is set
unset DJANGO_ENVIRONMENT

# Run commands normally
python manage.py runserver
python manage.py migrate
```

**Method 2: Explicit environment variable**
```bash
# Set for single command
DJANGO_ENVIRONMENT=development python manage.py runserver

# Or export for entire session
export DJANGO_ENVIRONMENT=development
python manage.py runserver
```

**Development Settings Include:**
- DEBUG = True
- PostgreSQL database (local)
- Redis cache (local)
- Console logging
- CORS allowed for localhost:5173
- Non-secure cookies (HTTP allowed)

### 2. Testing Environment

**For running tests:**
```bash
# Set environment explicitly
export DJANGO_ENVIRONMENT=testing

# Run tests
python manage.py test

# Or run specific tests
python manage.py test journal.tests
```

**Testing Settings Include:**
- SQLite database (fast, no setup)
- In-memory cache (LocMemCache)
- Console email backend
- Synchronous Celery (no worker needed)
- Disabled throttling (tests run faster)
- Null logging (no console spam)

### 3. Production Environment

**For production deployment:**
```bash
# Set environment variable in your deployment config
export DJANGO_ENVIRONMENT=production

# Verify settings
python manage.py check --deploy

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Start with gunicorn
gunicorn django_backend.wsgi:application
```

**Production Settings Include:**
- DEBUG = False
- Security headers (HSTS, SSL redirect, etc.)
- Database connection pooling (600s)
- Query timeout (30s)
- Redis cache (remote)
- JSON logging with file rotation
- Secure cookies (HTTPS only)

## Troubleshooting

### Problem: Wrong environment is loading

**Symptom:** You set `DJANGO_ENVIRONMENT=development` in `.env`, but testing settings load.

**Solution:**
```bash
# Check terminal environment variable
echo $DJANGO_ENVIRONMENT

# If it shows 'testing' or any value, unset it
unset DJANGO_ENVIRONMENT

# Now the .env file will be read
python manage.py check
# Should show: "✓ Development settings loaded"
```

### Problem: Production settings fail with logging error

**Error:** `ModuleNotFoundError: No module named 'pythonjsonlogger'`

**Solution:**
```bash
# Install the required package
pip install python-json-logger

# Or install all production requirements
pip install -r requirements/production.txt
```

### Problem: Can't connect to PostgreSQL in development

**Solution:**
```bash
# Option 1: Use SQLite instead (comment out PostgreSQL in development.py)
# Option 2: Install and start PostgreSQL
sudo systemctl start postgresql
createdb bo_journal
```

## Quick Reference

### Check Current Environment
```bash
python manage.py shell -c "from decouple import config; print(config('DJANGO_ENVIRONMENT', default='development'))"
```

### Verify Settings Are Correct
```bash
# Development
DJANGO_ENVIRONMENT=development python manage.py check

# Testing
DJANGO_ENVIRONMENT=testing python manage.py check

# Production
DJANGO_ENVIRONMENT=production python manage.py check --deploy
```

### Switch Environments
```bash
# Switch to testing
export DJANGO_ENVIRONMENT=testing
python manage.py test

# Switch back to development (unset to use .env)
unset DJANGO_ENVIRONMENT
python manage.py runserver

# Or set explicitly
export DJANGO_ENVIRONMENT=development
python manage.py runserver
```

## Best Practices

1. **Development**: Use `.env` file, keep terminal clean (no exported DJANGO_ENVIRONMENT)
2. **Testing**: Export `DJANGO_ENVIRONMENT=testing` before running tests
3. **Production**: Set in deployment config (systemd, Docker, etc.), never in code
4. **CI/CD**: Set in pipeline environment variables
5. **Never commit** `.env` file with production secrets

## Environment Settings Comparison

| Setting | Development | Testing | Production |
|---------|-------------|---------|------------|
| DEBUG | True | True | False |
| Database | PostgreSQL | SQLite | PostgreSQL |
| Cache | Redis | LocMemCache | Redis |
| Celery | Async | Sync (eager) | Async |
| Email | SMTP | Console | SMTP |
| Logging | Console | Null | JSON + File |
| SSL | Disabled | Disabled | Enforced |
| Throttling | Enabled | Disabled | Enabled |
| SECRET_KEY | Dev key | Test key | From env var |

## Additional Resources

- Settings structure: `django_backend/settings/`
- Base settings: `django_backend/settings/base.py`
- Environment-specific: `development.py`, `testing.py`, `production.py`
- Environment loader: `django_backend/settings/__init__.py`
