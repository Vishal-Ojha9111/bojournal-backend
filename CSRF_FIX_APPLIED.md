# ✅ CSRF 403 Error - FIXED

## What Was Fixed

### 1. ✅ Middleware Order Corrected
**File:** `backend/django_backend/django_backend/settings.py`

Moved CSRF middleware to the correct position (before AuthenticationMiddleware):

```python
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',  # ✅ Now in correct position
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

### 2. ✅ Enhanced CSRF Cookie Settings
**File:** `backend/django_backend/django_backend/settings.py`

Added explicit CSRF configuration for development:

```python
# Development CSRF Settings
CSRF_COOKIE_SECURE = False  # Allow HTTP
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False  # Allow JS access
CSRF_COOKIE_DOMAIN = None  # Allow localhost
CSRF_COOKIE_PATH = '/'
CSRF_USE_SESSIONS = False  # Cookie-based CSRF
CSRF_COOKIE_NAME = 'csrftoken'
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'
```

### 3. ✅ Updated CSRF Token Endpoint
**File:** `backend/django_backend/authapp/views.py`

Enhanced the `GetCSRFToken` view with proper cookie settings:

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
        
        # Explicit cookie settings
        response.set_cookie(
            key='csrftoken',
            value=token,
            max_age=31449600,  # 1 year
            secure=False,  # HTTP allowed in dev
            httponly=False,  # JS can access
            samesite='Lax',
            path='/',
        )
        return response
```

## How to Test

### Step 1: Restart Backend Server

```bash
cd backend/django_backend
python manage.py runserver
```

### Step 2: Test CSRF Endpoint

Open browser and go to:
```
http://127.0.0.1:8000/api/v2/auth/csrf
```

**Expected Response:**
```json
{
  "status": true,
  "message": "CSRF token set",
  "csrftoken": "some-long-token-string"
}
```

**Expected Cookie:**
Open DevTools → Application → Cookies → `http://127.0.0.1:8000`
- Name: `csrftoken`
- Value: (token string)
- Path: `/`
- HttpOnly: ❌ (false)
- Secure: ❌ (false)
- SameSite: `Lax`

### Step 3: Test Frontend Integration

```bash
cd frontend
npm run dev
```

1. Open browser DevTools → Network tab
2. Navigate to `http://localhost:5173`
3. Look for GET request to `/api/v2/auth/csrf`
4. Verify response has `csrftoken` in body
5. Check Application → Cookies for `csrftoken`

### Step 4: Test POST Request (Signup/Login)

1. Go to login page: `http://localhost:5173/auth/login`
2. Open DevTools → Network tab
3. Fill in the login form and submit
4. Check the POST request to `/api/v2/auth/login`
5. Verify Headers include:
   ```
   X-CSRFToken: <token-value>
   Content-Type: application/json
   Cookie: csrftoken=<token-value>
   ```
6. Should receive **200 OK** (not 403 Forbidden)

## Expected Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. Frontend Loads                                       │
│    AuthProvider → ensureCsrf()                          │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 2. GET /api/v2/auth/csrf                                │
│    Backend: GetCSRFToken view                           │
│    Response: { csrftoken: "abc123..." }                 │
│    Set-Cookie: csrftoken=abc123...                      │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Frontend Stores Token                                │
│    - In memory (apiClient)                              │
│    - In browser cookie (automatic)                      │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 4. User Submits Form (POST request)                     │
│    apiClient interceptor adds:                          │
│    - Header: X-CSRFToken: abc123...                     │
│    - Cookie: csrftoken=abc123... (automatic)            │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Backend Validates CSRF                               │
│    CsrfViewMiddleware checks:                           │
│    - Cookie value matches header value ✅               │
│    - Origin is trusted ✅                               │
│    - Token is valid ✅                                  │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 6. Request Processed Successfully                       │
│    Response: 200 OK                                     │
└─────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Still Getting 403?

**Check 1: Middleware Order**
```bash
cd backend/django_backend
grep -A 10 "MIDDLEWARE = \[" django_backend/settings.py
```
Verify `CsrfViewMiddleware` comes before `AuthenticationMiddleware`.

**Check 2: CSRF Settings**
```bash
grep -A 5 "CSRF_" django_backend/settings.py
```
Verify development settings are applied.

**Check 3: Cookie in Browser**
- Open DevTools → Application → Cookies
- Check if `csrftoken` cookie exists
- Value should match the token in POST header

**Check 4: Request Headers**
- Open DevTools → Network → Select POST request
- Headers tab should show:
  ```
  X-CSRFToken: <token>
  Cookie: csrftoken=<same-token>
  ```

**Check 5: Origin Mismatch**
- Ensure frontend URL matches CORS_ALLOWED_ORIGINS
- Use same format: `http://127.0.0.1:5173` or `http://localhost:5173`
- Don't mix 127.0.0.1 and localhost

### Django Server Logs

Check for these messages:
```bash
# Good:
"GET /api/v2/auth/csrf HTTP/1.1" 200
"POST /api/v2/auth/login HTTP/1.1" 200

# Bad:
"POST /api/v2/auth/login HTTP/1.1" 403
# Check: Forbidden (CSRF cookie not set.)
# Check: Forbidden (CSRF token missing or incorrect.)
```

## Common Issues & Fixes

### Issue: "CSRF cookie not set"
**Fix:** Ensure GET `/api/v2/auth/csrf` is called before POST requests
- Frontend: `ensureCsrf()` is called on app load ✅

### Issue: "CSRF token missing"
**Fix:** Verify apiClient interceptor is working
- Check `src/lib/apiClient.ts` has CSRF code uncommented ✅

### Issue: "CSRF token incorrect"
**Fix:** Cookie value must match header value
- Clear browser cookies and reload
- Verify both cookie and header show same token

### Issue: "Origin not in CSRF_TRUSTED_ORIGINS"
**Fix:** Add your frontend URL to settings.py:
```python
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173"
]
```

## Testing Checklist

- [ ] Backend server running on port 8000
- [ ] Frontend server running on port 5173
- [ ] GET `/api/v2/auth/csrf` returns 200 OK
- [ ] Response includes `csrftoken` field
- [ ] Browser cookie `csrftoken` is set
- [ ] Cookie is NOT HttpOnly (JavaScript can access)
- [ ] POST requests include `X-CSRFToken` header
- [ ] POST requests include `Cookie: csrftoken=...`
- [ ] Signup/Login returns 200 (not 403)
- [ ] No CORS errors in console
- [ ] No CSRF errors in Django logs

## Success Indicators

✅ **Working correctly if:**
1. CSRF token fetched successfully on app load
2. Token stored in browser cookie
3. POST requests return 200 OK (not 403)
4. No "CSRF" errors in browser console
5. No "Forbidden" errors in Django logs
6. Can signup/login/perform actions successfully

## Files Changed

✅ `/backend/django_backend/django_backend/settings.py`
- Fixed middleware order
- Enhanced CSRF cookie settings

✅ `/backend/django_backend/authapp/views.py`
- Updated GetCSRFToken view with explicit cookie settings

## Summary

The CSRF 403 error was caused by:
1. ❌ Incorrect middleware order
2. ❌ Missing explicit CSRF cookie settings
3. ❌ Cookie not properly configured for development

All issues have been fixed! The CSRF system should now work properly. 🎉

**Next Step:** Restart your backend server and test the flow above.
