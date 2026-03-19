# BO Journal - API Documentation (Part 3)

## Authentication Flows

### Signup Flow

Complete user registration process:

```
1. User fills signup form
   ↓
2. POST /api/v2/auth/signup
   {
     "first_name": "John",
     "last_name": "Doe",
     "email": "john@example.com",
     "password": "SecurePass123",
     "referral_code": "FRIEND2024"  // optional
   }
   ↓
3. Backend sends OTP to email
   Response: { "status": true, "message": "OTP sent to email." }
   ↓
4. User enters OTP
   ↓
5. POST /api/v2/auth/verifyotp
   {
     "email": "john@example.com",
     "otp": "123456"
   }
   ↓
6. Backend creates user & sets JWT cookies
   Response: {
     "status": true,
     "message": "User registered successfully.",
     "user": { ... }
   }
   ↓
7. User is logged in automatically
   (boj_token and boj_refresh_token cookies set)
```

**Frontend Implementation:**
```javascript
// Step 1: Signup
const signup = async (userData) => {
  const response = await fetch('/api/v2/auth/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userData)
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message);
  }
  
  return await response.json();
};

// Step 2: Verify OTP
const verifyOTP = async (email, otp) => {
  const response = await fetch('/api/v2/auth/verifyotp', {
    method: 'POST',
    credentials: 'include',  // Important: receive cookies
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, otp })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message);
  }
  
  const data = await response.json();
  return data.user;  // User is now logged in
};
```

---

### Login Flow

Standard authentication:

```
1. User enters credentials
   ↓
2. POST /api/v2/auth/login
   {
     "email": "john@example.com",
     "password": "SecurePass123"
   }
   ↓
3. Backend validates credentials
   ↓
4. Backend sets JWT cookies
   Response: {
     "status": true,
     "message": "Login successful.",
     "user": { ... }
   }
   ↓
5. User is logged in
   (boj_token and boj_refresh_token cookies set)
   ↓
6. Redirect to dashboard
```

**Frontend Implementation:**
```javascript
const login = async (email, password) => {
  const response = await fetch('/api/v2/auth/login', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message);
  }
  
  const data = await response.json();
  return data.user;
};
```

---

### Password Reset Flow

Complete password recovery process:

```
1. User clicks "Forgot Password"
   ↓
2. POST /api/v2/auth/resetpassword
   { "email": "john@example.com" }
   ↓
3. Backend sends OTP to email
   Backend sets 'prc' cookie (password reset context)
   Response: { "status": true, "message": "OTP sent to email for password reset." }
   ↓
4. User enters OTP
   ↓
5. POST /api/v2/auth/verifyotp
   { "email": "john@example.com", "otp": "123456" }
   ↓
6. Backend extends 'prc' cookie (10 min validity)
   Response: { "status": true, "message": "otp verified successfully" }
   ↓
7. User enters new password
   ↓
8. POST /api/v2/auth/updatepassword
   { "password": "NewSecurePass123" }
   ↓
9. Backend updates password & clears 'prc' cookie
   Response: { "message": "Password updated successfully. Try logging in with the new password." }
   ↓
10. Redirect to login page
```

**Frontend Implementation:**
```javascript
// Step 1: Request reset
const requestPasswordReset = async (email) => {
  const response = await fetch('/api/v2/auth/resetpassword', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email })
  });
  
  if (!response.ok) throw new Error('Failed to send OTP');
  return await response.json();
};

// Step 2: Verify OTP (same as signup)
const verifyResetOTP = async (email, otp) => {
  const response = await fetch('/api/v2/auth/verifyotp', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, otp })
  });
  
  if (!response.ok) throw new Error('Invalid OTP');
  return await response.json();
};

// Step 3: Update password
const updatePassword = async (newPassword) => {
  const response = await fetch('/api/v2/auth/updatepassword', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password: newPassword })
  });
  
  if (!response.ok) throw new Error('Failed to update password');
  return await response.json();
};
```

---

### Token Refresh Flow

Automatic token renewal:

```
1. User makes authenticated request
   ↓
2. Backend validates access token
   ↓
3a. Token is valid
    → Request succeeds
    
3b. Token is expired
    → Backend returns 401 Unauthorized
    ↓
4. Frontend intercepts 401 error
   ↓
5. POST /api/v2/auth/refresh
   (Automatically sends refresh token cookie)
   ↓
6a. Refresh token is valid
    → Backend sets new access token cookie
    → Retry original request
    
6b. Refresh token is expired
    → Redirect to login page
```

**Frontend Implementation:**
```javascript
// Axios interceptor for automatic token refresh
axios.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config;
    
    // If 401 and haven't retried yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        // Refresh token
        await fetch('/api/v2/auth/refresh', {
          method: 'POST',
          credentials: 'include'
        });
        
        // Retry original request
        return axios(originalRequest);
      } catch (refreshError) {
        // Refresh failed, redirect to login
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

// Or with fetch
const fetchWithAutoRefresh = async (url, options = {}) => {
  let response = await fetch(url, {
    ...options,
    credentials: 'include'
  });
  
  // If unauthorized, try refreshing token
  if (response.status === 401) {
    const refreshResponse = await fetch('/api/v2/auth/refresh', {
      method: 'POST',
      credentials: 'include'
    });
    
    if (refreshResponse.ok) {
      // Retry original request
      response = await fetch(url, {
        ...options,
        credentials: 'include'
      });
    } else {
      // Redirect to login
      window.location.href = '/login';
      throw new Error('Session expired');
    }
  }
  
  return response;
};
```

---

## Common Use Cases

### Use Case 1: First Time Setup

New user's complete onboarding:

```
1. Signup & Email Verification
   POST /api/v2/auth/signup
   POST /api/v2/auth/verifyotp
   
2. Create First Journal Entry
   POST /api/v2/journal/
   {
     "date": "2025-01-01",
     "opening_balance": "10000.00"
   }
   
3. Create Registers (Categories)
   POST /api/v2/registers/
   { "name": "Cash", "debit": true, "credit": true }
   
   POST /api/v2/registers/
   { "name": "Bank", "debit": true, "credit": true }
   
   POST /api/v2/registers/
   { "name": "Expenses", "debit": true, "credit": false }
   
   POST /api/v2/registers/
   { "name": "Income", "debit": false, "credit": true }
   
4. Purchase Subscription (if required features locked)
   GET /api/v2/payment/plans/
   GET /api/v2/payment/order/{planId}/
   POST /api/v2/payment/verify/
   
5. Ready to use!
```

**Frontend Implementation:**
```javascript
const firstTimeSetup = async () => {
  // 1. Create journal
  await fetch('/api/v2/journal/', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      date: '2025-01-01',
      opening_balance: '10000.00'
    })
  });
  
  // 2. Create default registers
  const registers = [
    { name: 'Cash', debit: true, credit: true },
    { name: 'Bank', debit: true, credit: true },
    { name: 'Expenses', debit: true, credit: false },
    { name: 'Income', debit: false, credit: true }
  ];
  
  for (const register of registers) {
    await fetch('/api/v2/registers/', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(register)
    });
  }
  
  // 3. Navigate to dashboard
  window.location.href = '/dashboard';
};
```

---

### Use Case 2: Daily Transaction Entry

Recording a daily transaction:

```
1. User enters transaction details
   ↓
2. (Optional) Upload receipt
   POST /api/v2/transactions/presign/
   PUT {presigned_url}  (direct to S3)
   ↓
3. Create transaction
   POST /api/v2/transactions/
   {
     "amount": "500.00",
     "description": "Office supplies",
     "transaction_type": "debit",
     "date": "2025-11-16",
     "register": 1,
     "image_keys": ["receipts/..."]  // if uploaded
   }
   ↓
4. View updated journal
   GET /api/v2/journal/?date=2025-11-16
```

**Frontend Implementation:**
```javascript
const createTransaction = async (transactionData, receiptFile) => {
  let imageKeys = [];
  
  // Upload receipt if provided
  if (receiptFile) {
    // Get presigned URL
    const presignResponse = await fetch('/api/v2/transactions/presign/', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        content_type: receiptFile.type,
        extension: receiptFile.name.split('.').pop(),
        key: 'transaction_receipt'
      })
    });
    
    const { upload_url, object_key } = await presignResponse.json();
    
    // Upload to S3
    await fetch(upload_url, {
      method: 'PUT',
      body: receiptFile,
      headers: { 'Content-Type': receiptFile.type }
    });
    
    imageKeys.push(object_key);
  }
  
  // Create transaction
  const response = await fetch('/api/v2/transactions/', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...transactionData,
      image_keys: imageKeys
    })
  });
  
  return await response.json();
};
```

---

### Use Case 3: Subscription Purchase

Complete payment flow:

```
1. User views plans
   GET /api/v2/payment/plans/
   
2. User selects plan
   ↓
3. Create Razorpay order
   GET /api/v2/payment/order/{planId}/
   Response includes: order_id, amount, key
   ↓
4. Open Razorpay checkout modal
   (Razorpay SDK handles payment)
   ↓
5. User completes payment
   Razorpay returns: payment_id, order_id, signature
   ↓
6. Verify payment
   POST /api/v2/payment/verify/
   {
     "razorpay_payment_id": "pay_...",
     "razorpay_order_id": "order_...",
     "razorpay_signature": "..."
   }
   ↓
7. Subscription activated!
   User's subscription_active = true
```

**Frontend Implementation:**
```javascript
const purchaseSubscription = async (planId) => {
  // 1. Create order
  const orderResponse = await fetch(`/api/v2/payment/order/${planId}/`, {
    credentials: 'include'
  });
  const { order } = await orderResponse.json();
  
  // 2. Open Razorpay checkout
  const options = {
    key: order.key,
    amount: order.amount,
    currency: order.currency,
    name: 'BO Journal',
    description: order.description,
    order_id: order.order_id,
    handler: async function(response) {
      // 3. Verify payment
      await fetch('/api/v2/payment/verify/', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          razorpay_payment_id: response.razorpay_payment_id,
          razorpay_order_id: response.razorpay_order_id,
          razorpay_signature: response.razorpay_signature
        })
      });
      
      // 4. Show success message
      alert('Subscription activated!');
      window.location.reload();
    },
    prefill: {
      email: user.email,
      name: `${user.first_name} ${user.last_name}`
    },
    theme: {
      color: '#3399cc'
    }
  };
  
  const rzp = new Razorpay(options);
  rzp.open();
};
```

---

### Use Case 4: Profile Picture Update

Upload and set profile picture:

```
1. User selects image
   ↓
2. Get presigned upload URL
   POST /api/v2/transactions/presign/
   {
     "content_type": "image/jpeg",
     "extension": "jpg",
     "key": "profile_picture"
   }
   ↓
3. Upload to S3
   PUT {presigned_url}
   ↓
4. Update user profile
   PATCH /api/v2/auth/user/update
   {
     "profile_picture_key": {
       "key": "profile-pictures/user-123/image.jpg"
     }
   }
   ↓
5. Get presigned view URL
   GET /api/v2/auth/user/profile-picture-url
   Response: { "url": "https://...", "expires_in": 600 }
   ↓
6. Display image
   <img src={url} />
```

**Frontend Implementation:**
```javascript
const updateProfilePicture = async (imageFile) => {
  // 1. Get presigned URL
  const presignResponse = await fetch('/api/v2/transactions/presign/', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      content_type: imageFile.type,
      extension: imageFile.name.split('.').pop(),
      key: 'profile_picture'
    })
  });
  
  const { upload_url, object_key } = await presignResponse.json();
  
  // 2. Upload to S3
  await fetch(upload_url, {
    method: 'PUT',
    body: imageFile,
    headers: { 'Content-Type': imageFile.type }
  });
  
  // 3. Update user profile
  await fetch('/api/v2/auth/user/update', {
    method: 'PATCH',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      profile_picture_key: { key: object_key }
    })
  });
  
  // 4. Get view URL
  const viewResponse = await fetch('/api/v2/auth/user/profile-picture-url', {
    credentials: 'include'
  });
  
  const { url } = await viewResponse.json();
  return url;
};
```

---

## Error Handling

### Standard Error Response Format

All errors follow this structure:

```json
{
  "status": false,
  "message": "Human-readable error message",
  "errors": {  // Optional, for validation errors
    "field_name": ["Error message 1", "Error message 2"]
  }
}
```

### HTTP Status Codes

| Code | Meaning | When It Occurs |
|------|---------|----------------|
| 400 | Bad Request | Invalid input, validation failed |
| 401 | Unauthorized | Not logged in, token expired |
| 403 | Forbidden | No subscription, not authorized |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource already exists |
| 500 | Internal Server Error | Server error, S3 error |
| 503 | Service Unavailable | Database/Redis/Celery down |

### Common Error Scenarios

#### 1. Authentication Errors

**Token Expired:**
```json
{
  "detail": "Token has expired"
}
```
**Action**: Call `/api/v2/auth/refresh`

**No Token:**
```json
{
  "status": false,
  "message": "Authentication credentials were not provided."
}
```
**Action**: Redirect to login

---

#### 2. Validation Errors

**Missing Required Field:**
```json
{
  "status": false,
  "message": "Validation error",
  "errors": {
    "amount": ["This field is required."],
    "date": ["This field is required."]
  }
}
```

**Invalid Format:**
```json
{
  "status": false,
  "message": "Invalid date format. Use YYYY-MM-DD."
}
```

---

#### 3. Business Logic Errors

**No Subscription:**
```json
{
  "status": false,
  "message": "Valid subscription required for this operation"
}
```
**Action**: Redirect to pricing page

**Future Date:**
```json
{
  "status": false,
  "message": "Cannot create transactions for future dates"
}
```

**Holiday Date:**
```json
{
  "status": false,
  "message": "Cannot create transactions on a holiday: Christmas Day"
}
```

---

#### 4. Resource Errors

**Not Found:**
```json
{
  "detail": "Not found."
}
```

**Already Exists:**
```json
{
  "status": false,
  "message": "Register with this name already exists."
}
```

**Cannot Delete:**
```json
{
  "status": false,
  "message": "Cannot delete register with existing transactions."
}
```

---

### Frontend Error Handling Best Practices

```javascript
// Comprehensive error handler
const handleApiError = async (response) => {
  if (response.ok) return response;
  
  const contentType = response.headers.get('content-type');
  let errorData;
  
  if (contentType && contentType.includes('application/json')) {
    errorData = await response.json();
  } else {
    errorData = { message: 'An unexpected error occurred' };
  }
  
  switch (response.status) {
    case 400:
      // Validation error
      if (errorData.errors) {
        // Show field-specific errors
        Object.entries(errorData.errors).forEach(([field, messages]) => {
          showFieldError(field, messages.join(', '));
        });
      } else {
        showErrorToast(errorData.message || 'Invalid input');
      }
      break;
      
    case 401:
      // Try to refresh token
      const refreshed = await refreshToken();
      if (!refreshed) {
        // Redirect to login
        window.location.href = '/login';
      }
      break;
      
    case 403:
      // Show subscription required message
      if (errorData.message?.includes('subscription')) {
        showSubscriptionModal();
      } else {
        showErrorToast('You do not have permission to perform this action');
      }
      break;
      
    case 404:
      showErrorToast('Resource not found');
      break;
      
    case 409:
      showErrorToast(errorData.message || 'Resource already exists');
      break;
      
    case 500:
      showErrorToast('Server error. Please try again later.');
      logErrorToService(errorData);  // Log for debugging
      break;
      
    case 503:
      showErrorToast('Service temporarily unavailable. Please try again.');
      break;
      
    default:
      showErrorToast('An unexpected error occurred');
  }
  
  throw new Error(errorData.message || 'API Error');
};

// Usage
try {
  const response = await fetch('/api/v2/transactions/', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(transactionData)
  });
  
  await handleApiError(response);
  const data = await response.json();
  // Success handling
} catch (error) {
  // Error already handled by handleApiError
  console.error('Transaction creation failed:', error);
}
```

---

## Rate Limiting

### Endpoints with Rate Limits

- `/api/v2/auth/signup` - 20 requests/minute
- `/api/v2/auth/login` - 20 requests/minute
- `/api/v2/auth/resetpassword` - 20 requests/minute
- `/api/v2/auth/verifyotp` - 20 requests/minute
- `/api/v2/auth/refresh` - 20 requests/minute
- All other authenticated endpoints - 100 requests/minute

### Rate Limit Headers

```
X-RateLimit-Limit: 20
X-RateLimit-Remaining: 15
X-RateLimit-Reset: 1605055200
```

### Rate Limit Exceeded Response

```json
{
  "detail": "Request was throttled. Expected available in 45 seconds."
}
```

**HTTP Status**: 429 Too Many Requests

---

## API Best Practices

### 1. Always Include Credentials
```javascript
fetch(url, {
  credentials: 'include'  // Required for cookies
})
```

### 2. Handle Token Refresh Automatically
Implement interceptor to refresh tokens on 401 errors.

### 3. Cache Data Appropriately
- User data: Cache for session
- Journal data: Cache for 5 minutes
- Plans: Cache for 1 hour

### 4. Show Loading States
API calls can take 200-2000ms. Always show loading indicators.

### 5. Validate Before Submitting
Client-side validation prevents unnecessary API calls.

### 6. Handle Offline Mode
Detect network errors and show appropriate messages.

### 7. Log Errors
Log errors to monitoring service for debugging.

---

## Testing the API

### Using cURL

**Login:**
```bash
curl -X POST https://api.example.com/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"email":"john@example.com","password":"SecurePass123"}'
```

**Authenticated Request:**
```bash
curl -X GET https://api.example.com/api/v2/journal/ \
  -b cookies.txt
```

### Using Postman

1. **Environment Variables:**
   - `base_url`: `https://api.example.com/api/v2`

2. **Cookie Handling:**
   - Enable "Automatically follow redirects"
   - Enable "Send cookies"

3. **Test Sequence:**
   - Login → Save cookies
   - Use cookies for subsequent requests

---

## Security Considerations

### 1. HTTPS Only
Always use HTTPS in production. HTTP-only cookies require HTTPS.

### 2. CORS Configuration
Backend must whitelist your frontend origin.

### 3. Cookie Security
- HTTP-only: JavaScript cannot access
- Secure: Only sent over HTTPS
- SameSite: CSRF protection

### 4. Input Validation
Always validate on client AND server.

### 5. Sensitive Data
Never log passwords, tokens, or payment details.

### 6. Rate Limiting
Respect rate limits to avoid blocking.

---

## Appendix

### Date Format Examples
```
Valid:   2025-11-16
Valid:   2025-01-01
Invalid: 11/16/2025
Invalid: 16-11-2025
Invalid: 2025/11/16
```

### Amount Format
```
Valid:   500.00
Valid:   500
Valid:   "500.00"
Valid:   "500"
Invalid: 500.
Invalid: .50
Invalid: 500.000
```

### Transaction Types
- `debit` - Money out, expense
- `credit` - Money in, income

### Subscription Status
- `subscription_active: true` - Active subscription
- `subscription_active: false` - No active subscription

---

**End of API Documentation**

For deployment instructions, see `PRODUCTION_DEPLOYMENT_GUIDE.md`.

For settings configuration, see `SETTINGS_USAGE_GUIDE.md`.

For questions or issues, contact the backend team.
