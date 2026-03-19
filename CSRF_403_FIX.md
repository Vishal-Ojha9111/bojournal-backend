# CSRF 403 Error - Diagnosis & Solutions

## 🔍 Problem Analysis

You're getting **403 Forbidden** errors when making POST/PUT/PATCH/DELETE requests because of CSRF token validation failures.

## 🎯 Root Causes Identified

### 1. **Middleware Order Issue** ⚠️
In `settings.py`, the CSRF middleware is placed AFTER the session middleware, but there's a potential ordering issue:

```python
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',          # Position 1 ✅
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',      # Position 8 ⚠️
]
```

**Problem**: CSRF middleware should come BEFORE AuthenticationMiddleware for proper token validation.

### 2. **CSRF Cookie Settings**
Current development settings:
```python
CSRF_COOKIE_SECURE = False  # ✅ Correct for HTTP
CSRF_COOKIE_SAMESITE = 'Lax'  # ⚠️ May block cross-origin requests
CSRF_COOKIE_HTTPONLY = False  # ✅ Correct (allows JS access)
```

### 3. **Missing CSRF Cookie Domain/Path**
The CSRF cookie might not have explicit domain and path settings, causing it to not be sent with requests.

### 4. **Frontend Headers Issue**
The frontend is sending `X-CSRFToken` but Django expects the exact format.

## 🔧 Solutions

### Solution 1: Fix Middleware Order (RECOMMENDED) ⭐

**File:** `backend/django_backend/django_backend/settings.py`

Move CSRF middleware to the correct position:

```python
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',      # ✅ MOVE HERE
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

### Solution 2: Add CSRF Cookie Configuration

Add these settings to the **development section** of `settings.py`:

```python
# Development CSRF Settings
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_DOMAIN = None  # Allow localhost
CSRF_COOKIE_PATH = '/'
CSRF_USE_SESSIONS = False  # Use cookie-based CSRF
CSRF_COOKIE_NAME = 'csrftoken'  # Explicit name
```

### Solution 3: Enhance CSRF View (Add Cookie Settings)

**File:** `backend/django_backend/authapp/views.py`

Update the `GetCSRFToken` view to properly set the cookie:

```python
class GetCSRFToken(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        token = get_token(request)
        response = Response({
            'status': True, 
            'message': 'CSRF token set', 
            'csrftoken': token
        }, status=status.HTTP_200_OK)
        
        # Set cookie with explicit settings for development
        response.set_cookie(
            key='csrftoken',
            value=token,
            max_age=31449600,  # 1 year
            secure=False,  # HTTP allowed in dev
            httponly=False,  # Allow JS access
            samesite='Lax',
            path='/',
            domain=None  # Allow localhost
        )
        return response
```

### Solution 4: Alternative - Exempt CSRF for API (Not Recommended for Production)

If you want to disable CSRF for specific API endpoints during development:

**File:** `backend/django_backend/authapp/views.py`

```python
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class SignupView(APIView):
    # ... existing code
```

⚠️ **WARNING**: Only use this for development. Never disable CSRF in production!

### Solution 5: Use DRF's SessionAuthentication (Alternative Approach)

If using DRF session auth, configure it properly:

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'core.authentication.JWTAuthentication',  # Your custom JWT
    ],
}
```

## 🚀 Recommended Implementation Steps

### Step 1: Fix Backend Settings

```python
# backend/django_backend/django_backend/settings.py

# Development section (after line 350)
else:
    # ... existing code ...
    
    # Enhanced CSRF Settings for Development
    CSRF_COOKIE_SECURE = False
    CSRF_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_HTTPONLY = False
    CSRF_COOKIE_DOMAIN = None
    CSRF_COOKIE_PATH = '/'
    CSRF_USE_SESSIONS = False
    CSRF_COOKIE_NAME = 'csrftoken'
    CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'  # Django expects this format
    
    # CORS Settings
    CORS_ALLOWED_ORIGINS = [
        "http://127.0.0.1:5173",
        "http://localhost:5173"
    ]
    
    CSRF_TRUSTED_ORIGINS = [
        "http://127.0.0.1:5173",
        "http://localhost:5173"
    ]
```

### Step 2: Fix Middleware Order

Move `'django.middleware.csrf.CsrfViewMiddleware'` to position after `CommonMiddleware` but before `AuthenticationMiddleware`.

### Step 3: Update CSRF View

```python
# backend/django_backend/authapp/views.py

class GetCSRFToken(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        token = get_token(request)
        response = Response({
            'status': True,
            'message': 'CSRF token set',
            'csrftoken': token
        }, status=status.HTTP_200_OK)
        
        # Explicitly set cookie with development-friendly settings
        response.set_cookie(
            key='csrftoken',
            value=token,
            max_age=31449600,
            secure=False,
            httponly=False,
            samesite='Lax',
            path='/',
        )
        return response
```

### Step 4: Verify Frontend Configuration

Ensure your frontend `.env` has:
```env
VITE_SERVER_URL=http://127.0.0.1:8000
VITE_API_BASE=http://127.0.0.1:8000/api/v2
VITE_PRODUCTION=False
```

## 🧪 Testing Steps

### 1. Test CSRF Token Fetch

```bash
curl -v http://127.0.0.1:8000/api/v2/auth/csrf \
  -H "Origin: http://localhost:5173" \
  -X GET
```

**Expected Response:**
- Status: 200 OK
- Headers: `Set-Cookie: csrftoken=...`
- Body: `{"status": true, "csrftoken": "..."}`

### 2. Test POST Request with CSRF

```bash
# First get CSRF token
CSRF_TOKEN=$(curl -s http://127.0.0.1:8000/api/v2/auth/csrf | jq -r '.csrftoken')

# Then use it in POST
curl -v http://127.0.0.1:8000/api/v2/auth/signup \
  -H "Origin: http://localhost:5173" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -X POST \
  -d '{"email":"test@example.com","password":"test123"}'
```

### 3. Test from Browser

1. Open DevTools → Application → Cookies
2. Visit: `http://localhost:5173`
3. Check Network tab for GET `/api/v2/auth/csrf`
4. Verify `csrftoken` cookie is set
5. Try signup/login - check POST request has `X-CSRFToken` header

## 🐛 Debug Checklist

- [ ] CSRF middleware is in correct position
- [ ] CSRF cookie settings are development-friendly
- [ ] `CORS_ALLOW_CREDENTIALS = True` is set
- [ ] Frontend uses `withCredentials: true` (already configured in apiClient)
- [ ] CSRF token is fetched before POST requests
- [ ] Cookie domain/path allows localhost
- [ ] Browser cookies show `csrftoken` after fetching
- [ ] POST requests include `X-CSRFToken` header
- [ ] Frontend and backend use same origin (127.0.0.1 or localhost)

## 💡 Quick Fix for Immediate Testing

If you need to test immediately without CSRF:

**Temporarily disable CSRF for API endpoints:**

```python
# backend/django_backend/django_backend/settings.py

# Add to development section
CSRF_COOKIE_HTTPONLY = False
CSRF_USE_SESSIONS = False

# OR use CSRF exempt decorator on specific views
from django.views.decorators.csrf import csrf_exempt
```

⚠️ Remember to re-enable CSRF for production!

## 📊 Common Error Patterns

### Error: "CSRF token missing"
- Frontend not sending `X-CSRFToken` header
- Token not fetched before POST
- Cookie not accessible to JavaScript

### Error: "CSRF token incorrect"
- Token mismatch between cookie and header
- Token expired (Django regenerates on logout)
- Wrong origin/domain

### Error: "CSRF cookie not set"
- Middleware order wrong
- Cookie settings too restrictive
- CORS not allowing credentials

## 🎯 Final Recommendation

**Implement Solutions 1, 2, and 3** for the most robust fix:
1. ✅ Fix middleware order
2. ✅ Add explicit CSRF cookie settings
3. ✅ Update GetCSRFToken view with proper cookie settings

This will ensure CSRF works properly in development while maintaining security.
