# BO Journal API v2 - Frontend Developer Guide

**API Version**: v2  
**Base URL (Development)**: `http://localhost:8000/api/v2/`  
**Base URL (Production)**: `https://your-domain.com/api/v2/`  
**Last Updated**: November 16, 2025

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication Flow](#authentication-flow)
3. [API Endpoints](#api-endpoints)
   - [Authentication](#authentication)
   - [User Management](#user-management)
   - [Journal Management](#journal-management)
   - [Transaction Management](#transaction-management)
   - [Register Management](#register-management)
   - [Holiday Management](#holiday-management)
   - [Payment Management](#payment-management)
4. [Operation Flows](#operation-flows)
5. [Error Handling](#error-handling)
6. [Best Practices](#best-practices)

---

## Quick Start

### Authentication Method

This API uses **JWT tokens stored in HTTP-only cookies**. You don't need to manually handle tokens in your code.

### CORS Configuration

Configure your frontend to include credentials:

```javascript
// fetch API
fetch(url, {
  credentials: 'include', // Always include this
  // ... other options
});

// axios
axios.defaults.withCredentials = true;
```

### Base Configuration

```javascript
// config.js
export const API_CONFIG = {
  BASE_URL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v2',
  TIMEOUT: 10000,
};

// api.js
import axios from 'axios';
import { API_CONFIG } from './config';

const api = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        await api.post('/auth/refresh');
        return api(originalRequest);
      } catch (refreshError) {
        // Redirect to login
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
```

---

## Authentication Flow

### JWT Token Lifecycle

- **Access Token**: 3 days (stored in HTTP-only cookie `access_token`)
- **Refresh Token**: 30 days (stored in HTTP-only cookie `refresh_token`)
- **Auto-refresh**: Interceptor automatically refreshes on 401 errors

### Authentication State Management

```javascript
// authContext.js
import { createContext, useContext, useState, useEffect } from 'react';
import api from './api';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const response = await api.get('/auth/check');
      setUser(response.data.data);
    } catch (error) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    const response = await api.post('/auth/login', { email, password });
    setUser(response.data.data.user);
    return response.data;
  };

  const logout = async () => {
    await api.post('/auth/logout');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
```

---

## API Endpoints

### Authentication

#### 1. Sign Up

**Endpoint**: `POST /auth/signup`

**Request Body**:
```json
{
  "email": "user@example.com",
  "name": "John Doe",
  "password": "SecurePass123!",
  "referred_by": "REF123" // Optional
}
```

**Success Response** (200):
```json
{
  "status": "success",
  "message": "OTP sent to email",
  "data": {
    "email": "user@example.com",
    "otp_expires_at": "2025-11-16T10:15:00Z"
  }
}
```

**Error Response** (400):
```json
{
  "status": "error",
  "message": "Email already exists"
}
```

**Frontend Implementation**:
```javascript
const signup = async (userData) => {
  try {
    const response = await api.post('/auth/signup', userData);
    
    // Show success message
    alert(response.data.message);
    
    // Navigate to OTP verification page
    navigate('/verify-otp', { state: { email: userData.email } });
    
    return response.data;
  } catch (error) {
    // Handle error
    const message = error.response?.data?.message || 'Signup failed';
    alert(message);
    throw error;
  }
};
```

---

#### 2. Verify OTP

**Endpoint**: `POST /auth/verify`

**Request Body**:
```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

**Success Response** (200):
```json
{
  "status": "success",
  "message": "Account created successfully",
  "data": {
    "user": {
      "id": 1,
      "email": "user@example.com",
      "name": "John Doe",
      "has_active_subscription": false,
      "subscription_expires_at": null
    }
  }
}
```
*Note: User is automatically logged in (cookies set)*

**Error Response** (400):
```json
{
  "status": "error",
  "message": "Invalid or expired OTP"
}
```

**Frontend Implementation**:
```javascript
const verifyOTP = async (email, otp) => {
  try {
    const response = await api.post('/auth/verify', { email, otp });
    
    // User is now logged in (cookies set automatically)
    const user = response.data.data.user;
    
    // Update auth context
    setUser(user);
    
    // Navigate to dashboard
    navigate('/dashboard');
    
    return response.data;
  } catch (error) {
    const message = error.response?.data?.message || 'Verification failed';
    alert(message);
    throw error;
  }
};
```

---

#### 3. Resend OTP

**Endpoint**: `POST /auth/signup`  
*(Same endpoint, if email exists in pending signups)*

**Request Body**:
```json
{
  "email": "user@example.com"
}
```

**Success Response** (200):
```json
{
  "status": "success",
  "message": "OTP resent to email"
}
```

---

#### 4. Login

**Endpoint**: `POST /auth/login`

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Success Response** (200):
```json
{
  "status": "success",
  "message": "Login successful",
  "data": {
    "user": {
      "id": 1,
      "email": "user@example.com",
      "name": "John Doe",
      "profile_picture": "https://s3.../profile.jpg",
      "has_active_subscription": true,
      "subscription_expires_at": "2026-11-16T00:00:00Z"
    }
  }
}
```

**Error Response** (401):
```json
{
  "status": "error",
  "message": "Invalid email or password"
}
```

**Frontend Implementation**:
```javascript
const login = async (email, password) => {
  try {
    const response = await api.post('/auth/login', { email, password });
    
    const user = response.data.data.user;
    setUser(user);
    
    // Navigate based on subscription status
    if (user.has_active_subscription) {
      navigate('/dashboard');
    } else {
      navigate('/subscription');
    }
    
    return response.data;
  } catch (error) {
    const message = error.response?.data?.message || 'Login failed';
    alert(message);
    throw error;
  }
};
```

---

#### 5. Logout

**Endpoint**: `POST /auth/logout`

**Request Body**: None

**Success Response** (200):
```json
{
  "status": "success",
  "message": "Logout successful"
}
```

**Frontend Implementation**:
```javascript
const logout = async () => {
  try {
    await api.post('/auth/logout');
    setUser(null);
    navigate('/login');
  } catch (error) {
    console.error('Logout failed:', error);
  }
};
```

---

#### 6. Check Authentication

**Endpoint**: `GET /auth/check`

**Success Response** (200):
```json
{
  "status": "success",
  "data": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe",
    "profile_picture": "https://s3.../profile.jpg",
    "has_active_subscription": true,
    "subscription_expires_at": "2026-11-16T00:00:00Z"
  }
}
```

**Error Response** (401):
```json
{
  "status": "error",
  "message": "Not authenticated"
}
```

---

#### 7. Refresh Token

**Endpoint**: `POST /auth/refresh`

**Request Body**: None

**Success Response** (200):
```json
{
  "status": "success",
  "message": "Token refreshed successfully"
}
```

**Error Response** (401):
```json
{
  "status": "error",
  "message": "Invalid refresh token"
}
```

*Note: This is automatically handled by the axios interceptor*

---

#### 8. Reset Password Request

**Endpoint**: `POST /auth/resetpassword`

**Request Body**:
```json
{
  "email": "user@example.com"
}
```

**Success Response** (200):
```json
{
  "status": "success",
  "message": "OTP sent to email for password reset",
  "data": {
    "email": "user@example.com",
    "otp_expires_at": "2025-11-16T10:15:00Z"
  }
}
```

**Frontend Implementation**:
```javascript
const requestPasswordReset = async (email) => {
  try {
    const response = await api.post('/auth/resetpassword', { email });
    alert(response.data.message);
    navigate('/verify-reset-otp', { state: { email } });
    return response.data;
  } catch (error) {
    const message = error.response?.data?.message || 'Request failed';
    alert(message);
    throw error;
  }
};
```

---

#### 9. Verify Reset OTP

**Endpoint**: `POST /auth/verify`

**Request Body**:
```json
{
  "email": "user@example.com",
  "otp": "123456",
  "action": "password_reset"
}
```

**Success Response** (200):
```json
{
  "status": "success",
  "message": "OTP verified. You can now update your password"
}
```

---

#### 10. Update Password

**Endpoint**: `POST /auth/updatepassword`

**Request Body**:
```json
{
  "email": "user@example.com",
  "otp": "123456",
  "new_password": "NewSecurePass123!"
}
```

**Success Response** (200):
```json
{
  "status": "success",
  "message": "Password updated successfully"
}
```

**Frontend Implementation**:
```javascript
const updatePassword = async (email, otp, newPassword) => {
  try {
    const response = await api.post('/auth/updatepassword', {
      email,
      otp,
      new_password: newPassword
    });
    
    alert(response.data.message);
    navigate('/login');
    return response.data;
  } catch (error) {
    const message = error.response?.data?.message || 'Update failed';
    alert(message);
    throw error;
  }
};
```

---

### User Management

#### 11. Update Profile

**Endpoint**: `PATCH /user/update`

**Request Body**:
```json
{
  "name": "John Updated",
  "profile_picture": "https://s3.amazonaws.com/bucket/profile.jpg"
}
```

**Success Response** (200):
```json
{
  "status": "success",
  "message": "Profile updated successfully",
  "data": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Updated",
    "profile_picture": "https://s3.amazonaws.com/bucket/profile.jpg"
  }
}
```

**Frontend Implementation**:
```javascript
const updateProfile = async (updates) => {
  try {
    const response = await api.patch('/user/update', updates);
    setUser(response.data.data);
    alert('Profile updated successfully');
    return response.data;
  } catch (error) {
    const message = error.response?.data?.message || 'Update failed';
    alert(message);
    throw error;
  }
};
```

---

#### 12. Get Profile Picture Upload URL

**Endpoint**: `GET /user/profile-picture-url?file_name=profile.jpg`

**Success Response** (200):
```json
{
  "status": "success",
  "data": {
    "upload_url": "https://s3.amazonaws.com/bucket/profile.jpg?signature=...",
    "file_url": "https://s3.amazonaws.com/bucket/profile.jpg",
    "expires_in": 600
  }
}
```

**Frontend Implementation**:
```javascript
const uploadProfilePicture = async (file) => {
  try {
    // Step 1: Get presigned URL
    const urlResponse = await api.get(
      `/user/profile-picture-url?file_name=${file.name}`
    );
    
    const { upload_url, file_url } = urlResponse.data.data;
    
    // Step 2: Upload file to S3
    await fetch(upload_url, {
      method: 'PUT',
      body: file,
      headers: {
        'Content-Type': file.type,
      },
    });
    
    // Step 3: Update user profile with S3 URL
    await api.patch('/user/update', {
      profile_picture: file_url
    });
    
    alert('Profile picture updated successfully');
    return file_url;
  } catch (error) {
    alert('Upload failed');
    throw error;
  }
};
```

---

### Journal Management

#### 13. List Journals

**Endpoint**: `GET /journal`

**Query Parameters**:
- `date` (optional): Filter by specific date (YYYY-MM-DD)
- `start_date` (optional): Filter from date
- `end_date` (optional): Filter to date

**Example**: `GET /journal?start_date=2025-11-01&end_date=2025-11-30`

**Success Response** (200):
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "date": "2025-11-16",
      "opening_balance": 50000.00,
      "closing_balance": 52000.00,
      "total_debit": 10000.00,
      "total_credit": 12000.00,
      "is_holiday": false,
      "transactions": [
        {
          "id": 1,
          "amount": 5000.00,
          "transaction_type": "debit",
          "register": {
            "id": 1,
            "name": "Office Expenses"
          },
          "remarks": "Office supplies",
          "image_url": "https://s3.../receipt.jpg",
          "created_at": "2025-11-16T10:00:00Z"
        }
      ]
    }
  ],
  "summary": {
    "total_journals": 30,
    "total_debit": 100000.00,
    "total_credit": 120000.00,
    "net_balance": 20000.00
  }
}
```

**Frontend Implementation**:
```javascript
const fetchJournals = async (startDate, endDate) => {
  try {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    
    const response = await api.get(`/journal?${params}`);
    return response.data;
  } catch (error) {
    console.error('Failed to fetch journals:', error);
    throw error;
  }
};
```

---

#### 14. Create First Journal Entry

**Endpoint**: `POST /journal/create-first-entry`

**Request Body**:
```json
{
  "date": "2025-01-01",
  "opening_balance": 50000.00
}
```

**Success Response** (201):
```json
{
  "status": "success",
  "message": "Journal entries created from 2025-01-01 to 2025-11-16",
  "data": {
    "journals_created": 320,
    "holidays_marked": 45,
    "opening_balance": 50000.00
  }
}
```

**Frontend Implementation**:
```javascript
const createFirstJournal = async (date, openingBalance) => {
  try {
    const response = await api.post('/journal/create-first-entry', {
      date,
      opening_balance: openingBalance
    });
    
    alert(response.data.message);
    return response.data;
  } catch (error) {
    const message = error.response?.data?.message || 'Creation failed';
    alert(message);
    throw error;
  }
};
```

---

#### 15. Update Opening Balance

**Endpoint**: `PATCH /journal/update-opening-balance`

**Request Body**:
```json
{
  "date": "2025-01-01",
  "new_opening_balance": 60000.00
}
```

**Success Response** (200):
```json
{
  "status": "success",
  "message": "Opening balance updated and all subsequent balances recalculated",
  "data": {
    "date": "2025-01-01",
    "old_opening_balance": 50000.00,
    "new_opening_balance": 60000.00,
    "journals_affected": 320
  }
}
```

---

### Transaction Management

#### 16. List Transactions

**Endpoint**: `GET /transactions`

**Query Parameters**:
- `date` (optional): Filter by date (YYYY-MM-DD)
- `start_date` (optional): Filter from date
- `end_date` (optional): Filter to date
- `register` (optional): Filter by register ID
- `transaction_type` (optional): Filter by type (debit/credit)

**Example**: `GET /transactions?date=2025-11-16&register=1`

**Success Response** (200):
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "date": "2025-11-16",
      "amount": 5000.00,
      "transaction_type": "debit",
      "register": {
        "id": 1,
        "name": "Office Expenses",
        "register_type": "debit"
      },
      "remarks": "Office supplies",
      "image_url": "https://s3.amazonaws.com/bucket/receipt.jpg",
      "created_at": "2025-11-16T10:00:00Z",
      "updated_at": "2025-11-16T10:00:00Z"
    }
  ]
}
```

---

#### 17. Create Transaction

**Endpoint**: `POST /transactions`

**Request Body**:
```json
{
  "date": "2025-11-16",
  "amount": 5000.00,
  "transaction_type": "debit",
  "register": 1,
  "remarks": "Office supplies",
  "image_url": "https://s3.amazonaws.com/bucket/receipt.jpg"
}
```

**Success Response** (201):
```json
{
  "status": "success",
  "message": "Transaction created successfully",
  "data": {
    "id": 1,
    "date": "2025-11-16",
    "amount": 5000.00,
    "transaction_type": "debit",
    "register": {
      "id": 1,
      "name": "Office Expenses"
    },
    "remarks": "Office supplies",
    "image_url": "https://s3.amazonaws.com/bucket/receipt.jpg"
  }
}
```

**Frontend Implementation**:
```javascript
const createTransaction = async (transactionData) => {
  try {
    const response = await api.post('/transactions', transactionData);
    alert('Transaction created successfully');
    return response.data;
  } catch (error) {
    const message = error.response?.data?.message || 'Creation failed';
    alert(message);
    throw error;
  }
};
```

---

#### 18. Get Transaction Upload URL

**Endpoint**: `POST /transactions/presigned-url`

**Request Body**:
```json
{
  "file_name": "receipt.jpg"
}
```

**Success Response** (200):
```json
{
  "status": "success",
  "data": {
    "upload_url": "https://s3.amazonaws.com/bucket/receipt.jpg?signature=...",
    "file_url": "https://s3.amazonaws.com/bucket/receipt.jpg",
    "expires_in": 600
  }
}
```

**Frontend Implementation**:
```javascript
const createTransactionWithImage = async (transactionData, imageFile) => {
  try {
    let imageUrl = null;
    
    // Step 1: Upload image if provided
    if (imageFile) {
      // Get presigned URL
      const urlResponse = await api.post('/transactions/presigned-url', {
        file_name: imageFile.name
      });
      
      const { upload_url, file_url } = urlResponse.data.data;
      
      // Upload to S3
      await fetch(upload_url, {
        method: 'PUT',
        body: imageFile,
        headers: {
          'Content-Type': imageFile.type,
        },
      });
      
      imageUrl = file_url;
    }
    
    // Step 2: Create transaction
    const response = await api.post('/transactions', {
      ...transactionData,
      image_url: imageUrl
    });
    
    alert('Transaction created successfully');
    return response.data;
  } catch (error) {
    alert('Failed to create transaction');
    throw error;
  }
};
```

---

#### 19. Update Transaction

**Endpoint**: `PUT /transactions/{id}`

**Request Body**:
```json
{
  "amount": 6000.00,
  "remarks": "Updated office supplies",
  "image_url": "https://s3.amazonaws.com/bucket/new-receipt.jpg"
}
```

**Success Response** (200):
```json
{
  "status": "success",
  "message": "Transaction updated successfully",
  "data": {
    "id": 1,
    "amount": 6000.00,
    "remarks": "Updated office supplies"
  }
}
```

---

#### 20. Delete Transaction

**Endpoint**: `DELETE /transactions/{id}`

**Success Response** (200):
```json
{
  "status": "success",
  "message": "Transaction deleted successfully"
}
```

**Frontend Implementation**:
```javascript
const deleteTransaction = async (id) => {
  if (!confirm('Are you sure you want to delete this transaction?')) {
    return;
  }
  
  try {
    await api.delete(`/transactions/${id}`);
    alert('Transaction deleted successfully');
    // Refresh transaction list
    fetchTransactions();
  } catch (error) {
    alert('Failed to delete transaction');
    throw error;
  }
};
```

---

### Register Management

#### 21. List Registers

**Endpoint**: `GET /registers`

**Success Response** (200):
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "name": "Office Expenses",
      "register_type": "debit",
      "created_at": "2025-11-01T00:00:00Z"
    },
    {
      "id": 2,
      "name": "Sales Revenue",
      "register_type": "credit",
      "created_at": "2025-11-01T00:00:00Z"
    }
  ]
}
```

---

#### 22. Create Register

**Endpoint**: `POST /registers`

**Request Body**:
```json
{
  "name": "Marketing Expenses",
  "register_type": "debit"
}
```

**Success Response** (201):
```json
{
  "status": "success",
  "message": "Register created successfully",
  "data": {
    "id": 3,
    "name": "Marketing Expenses",
    "register_type": "debit"
  }
}
```

**Frontend Implementation**:
```javascript
const createRegister = async (name, registerType) => {
  try {
    const response = await api.post('/registers', {
      name,
      register_type: registerType
    });
    
    alert('Register created successfully');
    return response.data;
  } catch (error) {
    const message = error.response?.data?.message || 'Creation failed';
    alert(message);
    throw error;
  }
};
```

---

#### 23. Update Register

**Endpoint**: `PUT /registers/{id}`

**Request Body**:
```json
{
  "name": "Updated Marketing Expenses"
}
```

**Success Response** (200):
```json
{
  "status": "success",
  "message": "Register updated successfully",
  "data": {
    "id": 3,
    "name": "Updated Marketing Expenses",
    "register_type": "debit"
  }
}
```

---

#### 24. Delete Register

**Endpoint**: `DELETE /registers/{id}`

**Success Response** (200):
```json
{
  "status": "success",
  "message": "Register deleted successfully"
}
```

**Error Response** (400):
```json
{
  "status": "error",
  "message": "Cannot delete register with existing transactions"
}
```

---

### Holiday Management

#### 25. List Holidays

**Endpoint**: `GET /holiday`

**Query Parameters**:
- `date` (optional): Specific date
- `start_date` (optional): From date
- `end_date` (optional): To date

**Success Response** (200):
```json
{
  "status": "success",
  "data": [
    {
      "date": "2025-11-16",
      "is_holiday": true,
      "has_transactions": false
    },
    {
      "date": "2025-11-17",
      "is_holiday": true,
      "has_transactions": false
    }
  ]
}
```

---

#### 26. Mark Holiday

**Endpoint**: `POST /holiday`

**Request Body**:
```json
{
  "date": "2025-11-25"
}
```

**Success Response** (200):
```json
{
  "status": "success",
  "message": "Holiday marked successfully",
  "data": {
    "date": "2025-11-25",
    "is_holiday": true
  }
}
```

---

#### 27. Remove Holiday

**Endpoint**: `DELETE /holiday`

**Request Body**:
```json
{
  "date": "2025-11-25"
}
```

**Success Response** (200):
```json
{
  "status": "success",
  "message": "Holiday removed successfully"
}
```

---

### Payment Management

#### 28. List Subscription Plans

**Endpoint**: `GET /payment/plans`  
*Note: This endpoint does NOT require authentication*

**Success Response** (200):
```json
{
  "status": "success",
  "data": [
    {
      "plan_id": "plan_monthly",
      "name": "Monthly Plan",
      "amount": 99.00,
      "currency": "INR",
      "period": "monthly",
      "interval": 1,
      "description": "Access for 1 month"
    },
    {
      "plan_id": "plan_yearly",
      "name": "Yearly Plan",
      "amount": 999.00,
      "currency": "INR",
      "period": "yearly",
      "interval": 1,
      "description": "Access for 12 months (Save 17%)"
    }
  ]
}
```

**Frontend Implementation**:
```javascript
const fetchPlans = async () => {
  try {
    const response = await api.get('/payment/plans');
    return response.data.data;
  } catch (error) {
    console.error('Failed to fetch plans:', error);
    throw error;
  }
};
```

---

#### 29. Create Razorpay Order

**Endpoint**: `POST /payment/create-order`

**Request Body**:
```json
{
  "plan_id": "plan_monthly"
}
```

**Success Response** (200):
```json
{
  "status": "success",
  "data": {
    "order_id": "order_MXx1234567890",
    "amount": 99.00,
    "currency": "INR",
    "razorpay_key": "rzp_test_abc123"
  }
}
```

**Frontend Implementation**:
```javascript
const createOrder = async (planId) => {
  try {
    const response = await api.post('/payment/create-order', {
      plan_id: planId
    });
    
    return response.data.data;
  } catch (error) {
    const message = error.response?.data?.message || 'Order creation failed';
    alert(message);
    throw error;
  }
};
```

---

#### 30. Verify Payment

**Endpoint**: `POST /payment/verify`

**Request Body**:
```json
{
  "razorpay_order_id": "order_MXx1234567890",
  "razorpay_payment_id": "pay_MXx1234567890",
  "razorpay_signature": "abc123..."
}
```

**Success Response** (200):
```json
{
  "status": "success",
  "message": "Payment verified and subscription activated",
  "data": {
    "payment_id": "pay_MXx1234567890",
    "order_id": "order_MXx1234567890",
    "subscription_expires_at": "2025-12-16T00:00:00Z"
  }
}
```

**Error Response** (400):
```json
{
  "status": "error",
  "message": "Payment verification failed"
}
```

---

#### 31. Get Payment History

**Endpoint**: `GET /payment/history`

**Success Response** (200):
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "order_id": "order_MXx1234567890",
      "payment_id": "pay_MXx1234567890",
      "amount": 99.00,
      "currency": "INR",
      "status": "completed",
      "plan_name": "Monthly Plan",
      "created_at": "2025-11-16T10:00:00Z"
    }
  ]
}
```

---

#### 32. Check Subscription Status

**Endpoint**: `GET /payment/status`

**Success Response** (200):
```json
{
  "status": "success",
  "data": {
    "has_active_subscription": true,
    "subscription_expires_at": "2025-12-16T00:00:00Z",
    "days_remaining": 30
  }
}
```

---

## Operation Flows

### 1. Complete Signup Flow

```javascript
// Step 1: User submits signup form
const handleSignup = async (formData) => {
  try {
    // Send signup request
    const response = await api.post('/auth/signup', {
      email: formData.email,
      name: formData.name,
      password: formData.password,
      referred_by: formData.referralCode || null
    });
    
    // Show success message
    alert('OTP sent to your email. Please check your inbox.');
    
    // Navigate to OTP verification page
    navigate('/verify-otp', { 
      state: { 
        email: formData.email,
        expiresAt: response.data.data.otp_expires_at
      } 
    });
    
  } catch (error) {
    if (error.response?.status === 400) {
      alert(error.response.data.message);
    } else {
      alert('Signup failed. Please try again.');
    }
  }
};

// Step 2: User enters OTP
const handleVerifyOTP = async (email, otp) => {
  try {
    const response = await api.post('/auth/verify', {
      email,
      otp
    });
    
    // User is now logged in (cookies set)
    const user = response.data.data.user;
    setUser(user);
    
    // Check subscription status
    if (user.has_active_subscription) {
      navigate('/dashboard');
    } else {
      navigate('/subscription');
    }
    
  } catch (error) {
    if (error.response?.status === 400) {
      alert(error.response.data.message);
      
      // If OTP expired or invalid
      if (error.response.data.message.includes('expired')) {
        // Show resend button
        setShowResend(true);
      }
    }
  }
};

// Step 3: Resend OTP if needed
const handleResendOTP = async (email) => {
  try {
    await api.post('/auth/signup', { email });
    alert('New OTP sent to your email');
    setShowResend(false);
  } catch (error) {
    alert('Failed to resend OTP');
  }
};
```

**Flow Diagram**:
```
User Fills Form
      ↓
POST /auth/signup
      ↓
OTP sent to email
      ↓
User enters OTP
      ↓
POST /auth/verify
      ↓
Account created + Auto login
      ↓
Check subscription
      ↓
Navigate to dashboard/subscription
```

---

### 2. Token Refresh Flow

```javascript
// Automatic token refresh (already configured in api.js)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If 401 error and haven't retried yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Attempt to refresh token
        await api.post('/auth/refresh');
        
        // Retry original request
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed - redirect to login
        localStorage.clear();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);
```

**Flow Diagram**:
```
API Request
      ↓
401 Unauthorized
      ↓
POST /auth/refresh
      ↓
Success?
   ↓     ↓
  Yes    No
   ↓     ↓
Retry  Logout
Request
```

---

### 3. Password Reset Flow

```javascript
// Step 1: Request password reset
const handleRequestReset = async (email) => {
  try {
    const response = await api.post('/auth/resetpassword', { email });
    
    alert('OTP sent to your email for password reset');
    
    navigate('/verify-reset-otp', {
      state: {
        email,
        expiresAt: response.data.data.otp_expires_at
      }
    });
    
  } catch (error) {
    alert(error.response?.data?.message || 'Request failed');
  }
};

// Step 2: Verify OTP
const handleVerifyResetOTP = async (email, otp) => {
  try {
    await api.post('/auth/verify', {
      email,
      otp,
      action: 'password_reset'
    });
    
    alert('OTP verified. Please enter your new password.');
    
    navigate('/update-password', {
      state: { email, otp }
    });
    
  } catch (error) {
    alert(error.response?.data?.message || 'Verification failed');
  }
};

// Step 3: Update password
const handleUpdatePassword = async (email, otp, newPassword) => {
  try {
    await api.post('/auth/updatepassword', {
      email,
      otp,
      new_password: newPassword
    });
    
    alert('Password updated successfully. Please login with your new password.');
    
    navigate('/login');
    
  } catch (error) {
    alert(error.response?.data?.message || 'Update failed');
  }
};
```

**Flow Diagram**:
```
User enters email
      ↓
POST /auth/resetpassword
      ↓
OTP sent to email
      ↓
User enters OTP
      ↓
POST /auth/verify (action=password_reset)
      ↓
OTP verified
      ↓
User enters new password
      ↓
POST /auth/updatepassword
      ↓
Password updated
      ↓
Navigate to login
```

---

### 4. Order Creation and Payment Verification Flow

```javascript
// Complete payment flow with Razorpay
const handleSubscriptionPurchase = async (planId) => {
  try {
    // Step 1: Create Razorpay order
    const orderResponse = await api.post('/payment/create-order', {
      plan_id: planId
    });
    
    const { order_id, amount, currency, razorpay_key } = orderResponse.data.data;
    
    // Step 2: Initialize Razorpay checkout
    const options = {
      key: razorpay_key,
      amount: amount * 100, // Convert to paise
      currency: currency,
      order_id: order_id,
      name: 'BO Journal',
      description: 'Subscription Payment',
      handler: async function (response) {
        // Step 3: Verify payment on backend
        try {
          const verifyResponse = await api.post('/payment/verify', {
            razorpay_order_id: response.razorpay_order_id,
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature: response.razorpay_signature
          });
          
          // Payment verified and subscription activated
          alert('Subscription activated successfully!');
          
          // Update user context
          await checkAuth();
          
          // Navigate to dashboard
          navigate('/dashboard');
          
        } catch (verifyError) {
          alert('Payment verification failed. Please contact support.');
          console.error('Verification error:', verifyError);
        }
      },
      modal: {
        ondismiss: function() {
          alert('Payment cancelled');
        }
      },
      theme: {
        color: '#3399cc'
      }
    };
    
    // Step 4: Open Razorpay checkout
    const rzp = new window.Razorpay(options);
    rzp.open();
    
  } catch (error) {
    alert('Failed to create order. Please try again.');
    console.error('Order creation error:', error);
  }
};

// Usage in component
const SubscriptionPage = () => {
  const [plans, setPlans] = useState([]);
  
  useEffect(() => {
    fetchPlans();
  }, []);
  
  const fetchPlans = async () => {
    try {
      const response = await api.get('/payment/plans');
      setPlans(response.data.data);
    } catch (error) {
      console.error('Failed to fetch plans:', error);
    }
  };
  
  return (
    <div>
      <h1>Choose Your Plan</h1>
      {plans.map(plan => (
        <div key={plan.plan_id}>
          <h2>{plan.name}</h2>
          <p>{plan.description}</p>
          <p>₹{plan.amount} / {plan.period}</p>
          <button onClick={() => handleSubscriptionPurchase(plan.plan_id)}>
            Subscribe Now
          </button>
        </div>
      ))}
    </div>
  );
};
```

**Flow Diagram**:
```
User selects plan
      ↓
POST /payment/create-order
      ↓
Backend creates Razorpay order
      ↓
Frontend opens Razorpay checkout
      ↓
User completes payment
      ↓
Razorpay callback with payment details
      ↓
POST /payment/verify
      ↓
Backend verifies signature
      ↓
Subscription activated
      ↓
Navigate to dashboard
```

---

### 5. Transaction with Image Upload Flow

```javascript
const handleCreateTransaction = async (transactionData, imageFile) => {
  try {
    let imageUrl = null;
    
    // Step 1: If image exists, get presigned URL
    if (imageFile) {
      const urlResponse = await api.post('/transactions/presigned-url', {
        file_name: imageFile.name
      });
      
      const { upload_url, file_url } = urlResponse.data.data;
      
      // Step 2: Upload image to S3
      const uploadResponse = await fetch(upload_url, {
        method: 'PUT',
        body: imageFile,
        headers: {
          'Content-Type': imageFile.type,
        },
      });
      
      if (!uploadResponse.ok) {
        throw new Error('Image upload failed');
      }
      
      imageUrl = file_url;
    }
    
    // Step 3: Create transaction with image URL
    const response = await api.post('/transactions', {
      date: transactionData.date,
      amount: parseFloat(transactionData.amount),
      transaction_type: transactionData.type,
      register: parseInt(transactionData.registerId),
      remarks: transactionData.remarks,
      image_url: imageUrl
    });
    
    alert('Transaction created successfully');
    
    // Refresh transaction list
    fetchTransactions();
    
    return response.data;
    
  } catch (error) {
    alert('Failed to create transaction');
    console.error('Transaction creation error:', error);
    throw error;
  }
};

// Usage in form component
const TransactionForm = () => {
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    amount: '',
    type: 'debit',
    registerId: '',
    remarks: ''
  });
  const [imageFile, setImageFile] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      await handleCreateTransaction(formData, imageFile);
      
      // Reset form
      setFormData({
        date: new Date().toISOString().split('T')[0],
        amount: '',
        type: 'debit',
        registerId: '',
        remarks: ''
      });
      setImageFile(null);
      
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <input
        type="date"
        value={formData.date}
        onChange={(e) => setFormData({...formData, date: e.target.value})}
        required
      />
      <input
        type="number"
        placeholder="Amount"
        value={formData.amount}
        onChange={(e) => setFormData({...formData, amount: e.target.value})}
        required
      />
      <select
        value={formData.type}
        onChange={(e) => setFormData({...formData, type: e.target.value})}
      >
        <option value="debit">Debit</option>
        <option value="credit">Credit</option>
      </select>
      <input
        type="file"
        accept="image/*"
        onChange={(e) => setImageFile(e.target.files[0])}
      />
      <button type="submit" disabled={loading}>
        {loading ? 'Creating...' : 'Create Transaction'}
      </button>
    </form>
  );
};
```

**Flow Diagram**:
```
User fills transaction form
      ↓
User selects image (optional)
      ↓
User submits form
      ↓
If image exists:
  POST /transactions/presigned-url
       ↓
  PUT to S3 presigned URL
       ↓
  Get file_url
      ↓
POST /transactions (with image_url)
      ↓
Transaction created
      ↓
Journal balances updated
      ↓
Refresh transaction list
```

---

## Error Handling

### Error Response Format

All errors follow this format:

```json
{
  "status": "error",
  "message": "Error description",
  "errors": {
    "field_name": ["Error message for field"]
  }
}
```

### Common HTTP Status Codes

- **200**: Success
- **201**: Created
- **400**: Bad Request (validation error)
- **401**: Unauthorized (not logged in or token expired)
- **403**: Forbidden (no permission)
- **404**: Not Found
- **429**: Too Many Requests (rate limited)
- **500**: Internal Server Error

### Global Error Handler

```javascript
// errorHandler.js
export const handleApiError = (error) => {
  if (error.response) {
    const status = error.response.status;
    const data = error.response.data;
    
    switch (status) {
      case 400:
        // Validation errors
        if (data.errors) {
          const messages = Object.values(data.errors).flat();
          return messages.join('\n');
        }
        return data.message || 'Invalid request';
        
      case 401:
        // Unauthorized - handled by interceptor
        return 'Please login to continue';
        
      case 403:
        return 'You do not have permission to perform this action';
        
      case 404:
        return 'Resource not found';
        
      case 429:
        return 'Too many requests. Please try again later';
        
      case 500:
        return 'Server error. Please try again later';
        
      default:
        return data.message || 'An error occurred';
    }
  }
  
  if (error.request) {
    return 'Network error. Please check your connection';
  }
  
  return 'An unexpected error occurred';
};

// Usage
try {
  await api.post('/auth/login', credentials);
} catch (error) {
  const message = handleApiError(error);
  alert(message);
}
```

### Validation Errors

```javascript
// Example: Signup with validation errors
try {
  await api.post('/auth/signup', {
    email: 'invalid-email',
    name: '',
    password: '123'
  });
} catch (error) {
  if (error.response?.status === 400) {
    const errors = error.response.data.errors;
    
    // errors = {
    //   "email": ["Enter a valid email address"],
    //   "name": ["This field is required"],
    //   "password": ["Password must be at least 8 characters"]
    // }
    
    // Display errors in form
    Object.keys(errors).forEach(field => {
      setFieldError(field, errors[field][0]);
    });
  }
}
```

---

## Best Practices

### 1. Always Include Credentials

```javascript
// fetch
fetch(url, {
  credentials: 'include'
});

// axios
axios.defaults.withCredentials = true;
```

### 2. Handle Token Refresh Automatically

Use the axios interceptor provided in the setup section.

### 3. Validate Before Submitting

```javascript
const validateTransaction = (data) => {
  const errors = {};
  
  if (!data.date) {
    errors.date = 'Date is required';
  }
  
  if (!data.amount || data.amount <= 0) {
    errors.amount = 'Amount must be greater than 0';
  }
  
  if (!data.registerId) {
    errors.register = 'Register is required';
  }
  
  return errors;
};
```

### 4. Show Loading States

```javascript
const [loading, setLoading] = useState(false);

const handleSubmit = async () => {
  setLoading(true);
  try {
    await api.post('/transactions', data);
  } finally {
    setLoading(false);
  }
};
```

### 5. Use Environment Variables

```javascript
// .env
REACT_APP_API_URL=http://localhost:8000/api/v2
REACT_APP_RAZORPAY_KEY=rzp_test_abc123

// config.js
export const config = {
  apiUrl: process.env.REACT_APP_API_URL,
  razorpayKey: process.env.REACT_APP_RAZORPAY_KEY
};
```

### 6. Cache API Responses

```javascript
// Use React Query or SWR
import { useQuery } from 'react-query';

const useJournals = (startDate, endDate) => {
  return useQuery(
    ['journals', startDate, endDate],
    () => api.get(`/journal?start_date=${startDate}&end_date=${endDate}`),
    {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
    }
  );
};
```

### 7. Format Dates Correctly

```javascript
// Always use YYYY-MM-DD format
const formatDate = (date) => {
  return new Date(date).toISOString().split('T')[0];
};

// Usage
const today = formatDate(new Date()); // "2025-11-16"
```

### 8. Handle File Uploads Properly

```javascript
// Check file size
if (file.size > 5 * 1024 * 1024) {
  alert('File size must be less than 5MB');
  return;
}

// Check file type
const allowedTypes = ['image/jpeg', 'image/png', 'image/jpg'];
if (!allowedTypes.includes(file.type)) {
  alert('Only JPEG and PNG images are allowed');
  return;
}
```

### 9. Implement Retry Logic for Failed Requests

```javascript
const retryRequest = async (fn, retries = 3) => {
  for (let i = 0; i < retries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === retries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
    }
  }
};

// Usage
const uploadImage = async () => {
  await retryRequest(() => 
    fetch(uploadUrl, { method: 'PUT', body: file })
  );
};
```

### 10. Log Errors for Debugging

```javascript
const logError = (error, context) => {
  console.error('Error:', {
    context,
    message: error.message,
    response: error.response?.data,
    status: error.response?.status,
    timestamp: new Date().toISOString()
  });
  
  // Send to error tracking service (Sentry, LogRocket, etc.)
  // errorTracker.captureException(error);
};
```

---

## Rate Limiting

- **Authentication endpoints** (`/auth/login`, `/auth/signup`, `/auth/resetpassword`): 20 requests per minute
- **All other endpoints**: 100 requests per minute

If you exceed the rate limit, you'll receive a `429 Too Many Requests` response.

---

## Date Format

All dates must be in **YYYY-MM-DD** format (e.g., `2025-11-16`).

---

## Amount Format

All amounts should be numbers with up to 2 decimal places (e.g., `5000.00`, `99.99`).

---

## Testing

### Using cURL

```bash
# Signup
curl -X POST http://localhost:8000/api/v2/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","name":"Test User","password":"Test123!"}'

# Login
curl -X POST http://localhost:8000/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"email":"test@example.com","password":"Test123!"}'

# Authenticated request
curl -X GET http://localhost:8000/api/v2/journal \
  -b cookies.txt
```

### Using Postman

1. Create a new request collection
2. Add environment variable: `base_url` = `http://localhost:8000/api/v2`
3. Enable "Automatically follow redirects"
4. Enable "Save cookies"
5. Test endpoints starting with `/auth/login`

---

## Support

For issues or questions:
- Check the error message in the response
- Review the operation flows in this guide
- Contact the backend team

---

**Happy Coding! 🚀**
