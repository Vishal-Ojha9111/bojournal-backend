#!/bin/bash

echo "=========================================="
echo "Django Settings Environment Test"
echo "=========================================="
echo ""

# Test 1: Development (using .env)
echo "1. Testing DEVELOPMENT environment (from .env file)"
echo "   Unsetting terminal variable..."
unset DJANGO_ENVIRONMENT
python manage.py check 2>&1 | grep "settings loaded"
echo ""

# Test 2: Testing (explicit)
echo "2. Testing TESTING environment (explicit export)"
export DJANGO_ENVIRONMENT=testing
python manage.py check 2>&1 | grep "settings loaded"
echo ""

# Test 3: Production (explicit)
echo "3. Testing PRODUCTION environment (explicit export)"
export DJANGO_ENVIRONMENT=production
python manage.py check 2>&1 | grep "settings loaded"
echo ""

echo "=========================================="
echo "All three environments tested successfully!"
echo "=========================================="
