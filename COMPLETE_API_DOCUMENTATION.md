# BO Journal - Complete API Documentation

**Version**: 2.0  
**Last Updated**: November 16, 2025  
**Base URL**: `https://your-domain.com/api/v2`  
**Development URL**: `http://localhost:8000/api/v2`

---

## Table of Contents

1. [Introduction](#introduction)
2. [Authentication](#authentication)
3. [Common Patterns](#common-patterns)
4. [Authentication Endpoints](#authentication-endpoints)
5. [User Management](#user-management)
6. [Journal Management](#journal-management)
7. [Transaction Management](#transaction-management)
8. [Register Management](#register-management)
9. [Holiday Management](#holiday-management)
10. [Payment Management](#payment-management)
11. [Authentication Flows](#authentication-flows)
12. [Common Use Cases](#common-use-cases)
13. [Error Handling](#error-handling)

---

## Introduction

The BO Journal API is a RESTful API for managing financial journals, transactions, and subscriptions. This documentation is intended for frontend developers integrating with the backend.

### Key Features
- JWT-based authentication with refresh tokens
- OTP-based email verification
- Financial journal and transaction management
- Register (category) system for transactions
- Holiday management
- Razorpay payment integration
- S3-based file uploads for receipts and profile pictures

### API Versioning
- **Current Version**: v2 (recommended)
- **Legacy Version**: v1 (backward compatible, use v2 for new development)

Both versions are accessible:
- v2: `/api/v2/{endpoint}`
- v1: `/api/{endpoint}` (legacy)

---

## Authentication

### Authentication Method
The API uses **JWT (JSON Web Tokens)** stored in **HTTP-only cookies** for security.

### Token Types
1. **Access Token** (`boj_token`)
   - Expires in 3 days
   - Used for authenticated API requests
   - Stored in HTTP-only cookie

2. **Refresh Token** (`boj_refresh_token`)
   - Expires in 30 days
   - Used to obtain new access tokens
   - Stored in HTTP-only cookie

### How Authentication Works
1. User logs in → Server sets cookies with tokens
2. Browser automatically sends cookies with each request
3. Server validates access token
4. If access token expires → Use refresh token to get new access token
5. If refresh token expires → User must log in again

### Making Authenticated Requests

**Important**: Include credentials in fetch requests:

```javascript
// Correct way to make authenticated requests
fetch('https://api.example.com/api/v2/journal/', {
  method: 'GET',
  credentials: 'include',  // This sends cookies automatically
  headers: {
    'Content-Type': 'application/json',
  }
})
```

### CORS Configuration
Frontend origins must be configured in backend `.env`:
```
ORIGIN0=https://yourdomain.com
ORIGIN1=http://localhost:5173
```

---

## Common Patterns

### Response Format

**Success Response:**
```json
{
  "status": true,
  "message": "Operation successful",
  "data": { ... }  // or "user", "journals", etc.
}
```

**Error Response:**
```json
{
  "status": false,
  "message": "Error description",
  "errors": { ... }  // Optional validation errors
}
```

### HTTP Status Codes
- `200 OK` - Success
- `201 Created` - Resource created
- `204 No Content` - Success, no content returned
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Not authenticated
- `403 Forbidden` - Not authorized (e.g., subscription required)
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource already exists
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service degraded

### Date Format
All dates use **ISO 8601** format: `YYYY-MM-DD`

Example: `2025-11-16`

### Pagination
Currently not implemented. All list endpoints return full datasets.

### Filtering
Many list endpoints support query parameters for filtering:
- `date` - Filter by specific date
- `start_date` - Filter from date
- `end_date` - Filter to date

Example: `/api/v2/journal/?start_date=2025-01-01&end_date=2025-12-31`

---

## Authentication Endpoints

### 1. User Signup

**Endpoint**: `POST /api/v2/auth/signup`  
**Authentication**: Not required  
**Rate Limit**: 20 requests/minute

Initiates user registration by sending an OTP to the email.

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "password": "SecurePassword123",
  "referral_code": "FRIEND2024"  // Optional
}
```

**Success Response** (200):
```json
{
  "status": true,
  "message": "OTP sent to email."
}
```

**Error Responses:**

Email already registered (400):
```json
{
  "status": false,
  "message": "Email already registered."
}
```

Invalid referral code (400):
```json
{
  "status": false,
  "message": "Invalid or expired referral code."
}
```

**Notes:**
- Password must be at least 6 characters
- OTP expires in 5 minutes (300 seconds)
- Maximum 10 OTP verification attempts allowed
- Exponential backoff enforced after failed attempts

---

### 2. Verify OTP

**Endpoint**: `POST /api/v2/auth/verifyotp`  
**Authentication**: Not required  
**Rate Limit**: 20 requests/minute

Verifies OTP and completes user registration or password reset.

**Request Body:**
```json
{
  "email": "john@example.com",
  "otp": "123456"
}
```

**Success Response - Signup** (201):
```json
{
  "status": true,
  "message": "User registered successfully.",
  "user": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "otp_verification": true,
    "subscription_active": false,
    "subscription_start_date": null,
    "subscription_end_date": null,
    "first_opening_balance": "0.00",
    "first_opening_balance_date": null,
    "register_types": [],
    "profile_picture_url": null
  }
}
```

**Success Response - Password Reset** (200):
```json
{
  "status": true,
  "message": "otp verified successfully"
}
```

**Error Responses:**

Invalid OTP (400):
```json
{
  "status": false,
  "message": "Invalid or expired OTP. 7 attempts remaining. Please wait 16 seconds before next attempt."
}
```

Max attempts exceeded (400):
```json
{
  "status": false,
  "message": "OTP expired due to maximum attempts exceeded. Please request a new OTP."
}
```

**Notes:**
- Sets JWT tokens in cookies upon successful signup
- Automatically logs in user after signup
- Sends welcome email (low priority, non-blocking)
- OTP is single-use and expires after verification

---

### 3. User Login

**Endpoint**: `POST /api/v2/auth/login`  
**Authentication**: Not required  
**Rate Limit**: 20 requests/minute

Authenticates user and sets JWT tokens.

**Request Body:**
```json
{
  "email": "john@example.com",
  "password": "SecurePassword123"
}
```

**Success Response** (200):
```json
{
  "status": true,
  "message": "Login successful.",
  "user": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "otp_verification": true,
    "subscription_active": true,
    "subscription_start_date": "2025-01-01",
    "subscription_end_date": "2026-01-01",
    "first_opening_balance": "10000.00",
    "first_opening_balance_date": "2025-01-01",
    "register_types": [
      {
        "id": 1,
        "register_name": "Cash",
        "debit": true,
        "credit": true
      }
    ],
    "profile_picture_url": "https://s3.amazonaws.com/..."
  }
}
```

**Error Responses:**

Invalid credentials (400):
```json
{
  "message": "Invalid email or password."
}
```

Account deactivated (403):
```json
{
  "message": "Account is deactivated."
}
```

**Notes:**
- Sets `boj_token` and `boj_refresh_token` cookies
- Cookies are HTTP-only and secure (in production)
- Access token expires in 3 days
- Refresh token expires in 30 days

---

### 4. Check Authentication

**Endpoint**: `GET /api/v2/auth/authcheck`  
**Authentication**: Required  

Verifies if the current user is authenticated and returns user data.

**Request:** No body required

**Success Response** (200):
```json
{
  "status": true,
  "user": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "subscription_active": true,
    "register_types": [...]
  }
}
```

**Error Response** (401):
```json
{
  "status": false,
  "message": "Authentication credentials were not provided."
}
```

**Usage:**
```javascript
// Check if user is logged in on app load
const checkAuth = async () => {
  const response = await fetch('https://api.example.com/api/v2/auth/authcheck', {
    credentials: 'include'
  });
  if (response.ok) {
    const data = await response.json();
    return data.user;
  }
  return null;
};
```

---

### 5. Refresh Access Token

**Endpoint**: `POST /api/v2/auth/refresh`  
**Authentication**: Requires refresh token cookie  
**Rate Limit**: 20 requests/minute

Obtains a new access token using the refresh token.

**Request:** No body required (uses refresh token from cookie)

**Success Response** (200):
```json
{
  "status": true,
  "message": "Token refreshed successfully.",
  "user": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    ...
  }
}
```

**Error Responses:**

No refresh token (401):
```json
{
  "status": false,
  "message": "Refresh token not found. Please log in again."
}
```

Invalid refresh token (401):
```json
{
  "status": false,
  "message": "Invalid or expired refresh token. Please log in again."
}
```

**Usage:**
```javascript
// Automatically refresh token when access token expires
const refreshToken = async () => {
  const response = await fetch('https://api.example.com/api/v2/auth/refresh', {
    method: 'POST',
    credentials: 'include'
  });
  return response.ok;
};

// Intercept 401 errors and refresh token
fetch('https://api.example.com/api/v2/journal/', {
  credentials: 'include'
})
.catch(async (error) => {
  if (error.status === 401) {
    const refreshed = await refreshToken();
    if (refreshed) {
      // Retry original request
      return fetch('https://api.example.com/api/v2/journal/', {
        credentials: 'include'
      });
    }
  }
  throw error;
});
```

---

### 6. Logout

**Endpoint**: `GET /api/v2/auth/logout`  
**Authentication**: Not required (clears cookies)

Logs out user by clearing authentication cookies.

**Request:** No body required

**Success Response** (200):
```json
{
  "status": true,
  "message": "Logout sucess."
}
```

**Usage:**
```javascript
const logout = async () => {
  await fetch('https://api.example.com/api/v2/auth/logout', {
    credentials: 'include'
  });
  // Redirect to login page
  window.location.href = '/login';
};
```

**Notes:**
- Deletes `boj_token` and `boj_refresh_token` cookies
- Always returns success (even if not logged in)

---

### 7. Request Password Reset

**Endpoint**: `POST /api/v2/auth/resetpassword`  
**Authentication**: Not required  
**Rate Limit**: 20 requests/minute

Sends OTP to email for password reset.

**Request Body:**
```json
{
  "email": "john@example.com"
}
```

**Success Response** (200):
```json
{
  "status": true,
  "message": "OTP sent to email for password reset."
}
```

**Error Responses:**

Email required (400):
```json
{
  "status": false,
  "message": "Email is required."
}
```

User not found (404):
```json
{
  "status": false,
  "message": "User does not exist."
}
```

**Notes:**
- Sets a signed cookie `prc` (password reset context) valid for 3 minutes
- OTP expires in 5 minutes
- After OTP verification, new cookie valid for 10 minutes to update password

---

### 8. Update Password

**Endpoint**: `POST /api/v2/auth/updatepassword`  
**Authentication**: Requires password reset cookie (set after OTP verification)

Updates user password after OTP verification.

**Request Body:**
```json
{
  "password": "NewSecurePassword123"
}
```

**Success Response** (200):
```json
{
  "message": "Password updated successfully. Try logging in with the new password."
}
```

**Error Responses:**

Session expired (400):
```json
{
  "message": "Session expired or invalid, Please try again later."
}
```

Password required (400):
```json
{
  "message": "Email and new password are required."
}
```

**Notes:**
- Must call `/verifyotp` first with password reset OTP
- Cookie expires 10 minutes after OTP verification
- Automatically clears password reset cookie

---

### 9. Get CSRF Token

**Endpoint**: `GET /api/v2/auth/csrf`  
**Authentication**: Not required

Gets CSRF token for forms (if needed).

**Request:** No body required

**Success Response** (200):
```json
{
  "status": true,
  "message": "CSRF token set",
  "csrftoken": "abc123..."
}
```

**Notes:**
- Generally not needed when using cookies
- Sets `csrftoken` cookie
- Only required for certain security configurations

---

### 10. Health Check

**Endpoint**: `GET /api/v2/auth/health`  
**Authentication**: Not required

Checks system health status (database, Redis, Celery).

**Request:** No body required

**Success Response** (200):
```json
{
  "status": "healthy",
  "timestamp": "2025-11-16T10:30:00Z",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    },
    "redis": {
      "status": "healthy",
      "message": "Redis cache operational"
    },
    "celery": {
      "status": "healthy",
      "workers": 2,
      "message": "2 worker(s) active"
    }
  }
}
```

**Degraded Response** (503):
```json
{
  "status": "degraded",
  "timestamp": "2025-11-16T10:30:00Z",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    },
    "redis": {
      "status": "unhealthy",
      "error": "Connection refused"
    },
    "celery": {
      "status": "unhealthy",
      "workers": 0,
      "message": "No Celery workers available"
    }
  }
}
```

**Usage:**
- Monitor application health
- Use in load balancers for health checks
- Diagnose system issues

---

## User Management

### 11. Update User Profile

**Endpoint**: `PATCH /api/v2/auth/user/update`  
**Authentication**: Required

Updates user profile information.

**Allowed Fields:**
- `first_name`
- `last_name`
- `profile_picture_key`

**Request Body:**
```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "profile_picture_key": {
    "key": "profile-pictures/user-123/image.jpg"
  }
}
```

**Success Response** (200):
```json
{
  "status": true,
  "message": "User updated.",
  "user": {
    "first_name": "Jane",
    "last_name": "Smith",
    "email": "jane@example.com",
    ...
  }
}
```

**Error Responses:**

Forbidden fields (400):
```json
{
  "status": false,
  "message": "Attempted to update forbidden fields.",
  "forbidden_fields": ["subscription_active", "subscription_end_date"]
}
```

No changes (400):
```json
{
  "status": false,
  "message": "No valid fields to update."
}
```

**Notes:**
- Cannot update subscription fields (protected)
- Cannot update email (use admin panel)
- Profile picture key should be S3 object key

---

### 12. Get Profile Picture URL

**Endpoint**: `GET /api/v2/auth/user/profile-picture-url`  
**Authentication**: Required

Generates a presigned URL for viewing the user's profile picture.

**Request:** No body required

**Success Response** (200):
```json
{
  "status": true,
  "url": "https://bucket-name.s3.amazonaws.com/profile-pictures/user-123/image.jpg?X-Amz-...",
  "expires_in": 600
}
```

**Error Responses:**

No profile picture (400):
```json
{
  "status": false,
  "message": "Invalid image key."
}
```

**Notes:**
- URL expires in 10 minutes (600 seconds) by default
- Must request new URL after expiration
- Returns HTTP 500 if S3 is unavailable

---

*[Continued in next section...]*
