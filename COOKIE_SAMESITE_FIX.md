# Cookie SameSite Configuration Fix - November 17, 2025

## 🐛 Issue Description

Cookies were not being set properly in development environment due to incorrect `SameSite` attribute configuration. The CSRF token cookie was not setting because `SameSite=Lax` was hardcoded and doesn't work for cross-origin requests between `localhost:5173` (frontend) and `localhost:8000` (backend).

**Impact**: 
- CSRF protection failing
- Authentication cookies not being received
- Password reset flow broken in development

## 🔍 Root Cause

**Different ports = Different origins** in browsers:
- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- `SameSite=Lax` blocks cookies on cross-origin AJAX requests

## ✅ Solution Applied

### 1. Updated Views to Use Environment Settings

**Files Modified**: `authapp/views.py` (3 locations)

Changed hardcoded cookie settings to use environment-specific configuration:

```python
# ✅ Now uses settings from environment
response.set_cookie(
    key='csrftoken',
    secure=settings.CSRF_COOKIE_SECURE,      # From settings
    samesite=settings.CSRF_COOKIE_SAMESITE,  # From settings
)
```

### 2. Updated Environment Settings

#### Development (`settings/development.py`)
```python
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_SAMESITE = None  # Allows cross-origin
JWT_COOKIE_SAMESITE = None
SESSION_COOKIE_SAMESITE = None
```

#### Testing (`settings/testing.py`)
```python
CSRF_COOKIE_SAMESITE = None
JWT_COOKIE_SAMESITE = None
SESSION_COOKIE_SAMESITE = None
```

#### Production (`settings/production.py`) - Already Correct
```python
CSRF_COOKIE_SECURE = True  # HTTPS required
CSRF_COOKIE_SAMESITE = 'None'
JWT_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SAMESITE = 'None'
```

## 📊 Cookie Configuration by Environment

| Environment | Secure | SameSite | Why? |
|-------------|--------|----------|------|
| Development | False | None | Allow cross-origin on different ports (HTTP) |
| Testing | False | None | Allow test client to set cookies |
| Production | True | None | Allow cross-origin with HTTPS (Secure required) |

## 🧪 Testing

```bash
# Test CSRF endpoint
curl -i http://localhost:8000/api/v2/auth/csrf

# Check for header: Set-Cookie: csrftoken=...; SameSite=None
```

```javascript
// From frontend
const response = await fetch('http://localhost:8000/api/v2/auth/csrf', {
  credentials: 'include'  // REQUIRED
});

console.log(document.cookie); // Should show csrftoken
```

## 🔒 Security Notes

- **Development**: `SameSite=None` + `Secure=False` is safe (local only)
- **Production**: `SameSite=None` + `Secure=True` is safe (HTTPS + CORS protection)
- **CSRF protection** still active via token validation
- **JWT tokens** remain HttpOnly (JavaScript cannot access)

## 📝 Frontend Requirement

**CRITICAL**: Always use `credentials: 'include'`

```javascript
// Axios
axios.defaults.withCredentials = true;

// Fetch
fetch(url, { credentials: 'include' });
```

## 📚 Files Modified

1. ✅ `authapp/views.py` - GetCSRFToken, ResetPasswordView, VerifyOTPView
2. ✅ `settings/development.py` - CSRF, JWT, Session cookies
3. ✅ `settings/testing.py` - CSRF, JWT, Session cookies

## 🎯 Result

- ✅ CSRF tokens now set correctly in development
- ✅ JWT authentication cookies working
- ✅ Password reset cookies working
- ✅ All cookies work across environments
- ✅ Production security maintained

---

**Status**: ✅ **RESOLVED**  
**Date**: November 17, 2025  
**Severity**: High
