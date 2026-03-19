# BO Journal - API Documentation (Part 2)

## Journal Management

### 13. List Journals

**Endpoint**: `GET /api/v2/journal/`  
**Authentication**: Required

Retrieves user's journal entries with transactions.

**Query Parameters:**
- `date` - Specific date (YYYY-MM-DD)
- `start_date` - From date (YYYY-MM-DD)
- `end_date` - To date (YYYY-MM-DD)

**Request Examples:**
```
GET /api/v2/journal/?date=2025-11-16
GET /api/v2/journal/?start_date=2025-11-01&end_date=2025-11-30
GET /api/v2/journal/?start_date=2025-11-01
```

**Success Response** (200):
```json
{
  "status": true,
  "message": "Journals retrieved successfully.",
  "journals": [
    {
      "id": 1,
      "date": "2025-11-16",
      "opening_balance": "10000.00",
      "closing_balance": "9500.00",
      "is_holiday": false,
      "holiday_reason": "",
      "transactions": [
        {
          "id": 1,
          "amount": "500.00",
          "transaction_type": "debit",
          "description": "Office supplies",
          "date": "2025-11-16",
          "register": {
            "id": 1,
            "name": "Expenses"
          },
          "image_keys": ["receipts/transaction-1/receipt.jpg"],
          "created_at": "2025-11-16T10:30:00Z"
        }
      ]
    }
  ],
  "summary": {
    "total_debit": "500.00",
    "total_credit": "0.00",
    "net_change": "-500.00",
    "start_balance": "10000.00",
    "end_balance": "9500.00"
  }
}
```

**Error Responses:**

No opening balance set (400):
```json
{
  "status": false,
  "message": "Set first opening balance first."
}
```

No journals found (404):
```json
{
  "status": false,
  "message": "No journals found for the specified date or range."
}
```

**Notes:**
- Response is cached for 5 minutes
- Returns journals ordered by date ascending
- Each journal includes all transactions for that date
- Holiday journals have no transactions

---

### 14. Create First Journal Entry

**Endpoint**: `POST /api/v2/journal/`  
**Authentication**: Required  
**Subscription**: Required

Creates the first journal entry and sets opening balance.

**Request Body:**
```json
{
  "date": "2025-01-01",
  "opening_balance": "10000.00"
}
```

**Success Response** (201):
```json
{
  "status": true,
  "message": "Journals created successfully from 2025-01-01 to 2025-11-16",
  "data": [
    {
      "id": 1,
      "date": "2025-01-01",
      "opening_balance": "10000.00",
      "closing_balance": "10000.00",
      "is_holiday": false
    },
    ...
  ]
}
```

**Error Responses:**

No subscription (403):
```json
{
  "status": false,
  "message": "Valid subscription required for this operation"
}
```

Journal already exists (409):
```json
{
  "status": false,
  "message": "Journal already exists for this user."
}
```

**Notes:**
- Can only be called once per user
- Creates journal entries from specified date to today
- Sundays are automatically marked as holidays
- Sets `first_opening_balance` and `first_opening_balance_date` on user
- Invalidates journal cache

---

### 15. Update Opening Balance

**Endpoint**: `PATCH /api/v2/journal/`  
**Authentication**: Required  
**Subscription**: Required

Updates the opening balance for the first journal entry.

**Request Body:**
```json
{
  "date": "2025-01-01",
  "opening_balance": "15000.00"
}
```

**Success Response** (200):
```json
{
  "status": true,
  "message": "Journal updated with new opening balance successfully."
}
```

**Error Responses:**

Date mismatch (400):
```json
{
  "status": false,
  "message": "Date must match your first opening balance date to update."
}
```

**Notes:**
- Date must match existing `first_opening_balance_date`
- Recalculates all subsequent journal balances
- Invalidates journal cache

---

## Transaction Management

### 16. List Transactions

**Endpoint**: `GET /api/v2/transactions/`  
**Authentication**: Required

Retrieves user's transactions with filtering.

**Query Parameters:**
- `date` - Specific date
- `start_date` - From date
- `end_date` - To date
- `register` - Filter by register ID
- `transaction_type` - Filter by type (`debit` or `credit`)

**Request Example:**
```
GET /api/v2/transactions/?start_date=2025-11-01&transaction_type=debit
```

**Success Response** (200):
```json
{
  "results": [
    {
      "id": 1,
      "amount": "500.00",
      "description": "Office supplies",
      "transaction_type": "debit",
      "date": "2025-11-16",
      "register": {
        "id": 1,
        "name": "Expenses",
        "debit": true,
        "credit": false
      },
      "image_keys": ["receipts/trans-1/receipt.jpg"],
      "created_at": "2025-11-16T10:30:00Z",
      "updated_at": "2025-11-16T10:30:00Z"
    }
  ]
}
```

**Notes:**
- Returns transactions ordered by date (desc), then created_at (desc)
- Includes register details
- Image keys are S3 object keys

---

### 17. Create Transaction

**Endpoint**: `POST /api/v2/transactions/`  
**Authentication**: Required  
**Subscription**: Required

Creates a new transaction.

**Request Body:**
```json
{
  "amount": "500.00",
  "description": "Office supplies",
  "transaction_type": "debit",
  "date": "2025-11-16",
  "register": 1,
  "image_keys": ["receipts/trans-1/receipt.jpg"]
}
```

**Success Response** (201):
```json
{
  "id": 1,
  "amount": "500.00",
  "description": "Office supplies",
  "transaction_type": "debit",
  "date": "2025-11-16",
  "register": {
    "id": 1,
    "name": "Expenses",
    "debit": true,
    "credit": false
  },
  "image_keys": ["receipts/trans-1/receipt.jpg"],
  "created_at": "2025-11-16T10:30:00Z",
  "updated_at": "2025-11-16T10:30:00Z"
}
```

**Error Responses:**

Future date (400):
```json
{
  "status": false,
  "message": "Cannot create transactions for future dates"
}
```

Before first journal (400):
```json
{
  "status": false,
  "message": "Cannot create transaction before first entry of journal. Create transaction from or after date 2025-01-01"
}
```

Holiday date (400):
```json
{
  "status": false,
  "message": "Cannot create transactions on a holiday: National Holiday"
}
```

Invalid register type (400):
```json
{
  "status": false,
  "message": "Register 'Expenses' does not support credit transactions."
}
```

**Notes:**
- Amount must be positive
- Date cannot be in the future
- Date cannot be before first journal entry
- Date cannot be a holiday
- Register must support the transaction type
- Updates journal balances automatically
- Invalidates journal cache

---

### 18. Get Transaction Details

**Endpoint**: `GET /api/v2/transactions/{id}/`  
**Authentication**: Required

Retrieves a specific transaction.

**Success Response** (200):
```json
{
  "id": 1,
  "amount": "500.00",
  "description": "Office supplies",
  "transaction_type": "debit",
  "date": "2025-11-16",
  "register": {
    "id": 1,
    "name": "Expenses"
  },
  "image_keys": ["receipts/trans-1/receipt.jpg"]
}
```

**Error Response** (404):
```json
{
  "detail": "Not found."
}
```

---

### 19. Update Transaction

**Endpoint**: `PUT /api/v2/transactions/{id}/` or `PATCH /api/v2/transactions/{id}/`  
**Authentication**: Required  
**Subscription**: Required

Updates an existing transaction.

**Request Body (Full Update - PUT):**
```json
{
  "amount": "750.00",
  "description": "Updated description",
  "transaction_type": "debit",
  "date": "2025-11-16",
  "register": 1,
  "image_keys": ["receipts/trans-1/new-receipt.jpg"]
}
```

**Request Body (Partial Update - PATCH):**
```json
{
  "amount": "750.00",
  "description": "Updated description"
}
```

**Success Response** (200):
```json
{
  "id": 1,
  "amount": "750.00",
  "description": "Updated description",
  ...
}
```

**Error Responses:**

Future date (400):
```json
{
  "status": false,
  "message": "Cannot set transaction date to the future."
}
```

Holiday date (400):
```json
{
  "status": false,
  "message": "Cannot update transaction on a holiday: Weekend"
}
```

**Notes:**
- Old S3 images are deleted if image_keys change
- Updates both original and new date journals if date changes
- Invalidates journal cache

---

### 20. Delete Transaction

**Endpoint**: `DELETE /api/v2/transactions/{id}/`  
**Authentication**: Required

Deletes a transaction.

**Success Response** (204):
```
No content
```

**Notes:**
- Deletes S3 images if present
- Updates journal balances
- Invalidates journal cache
- Cannot be undone

---

### 21. Get Presigned Upload URL

**Endpoint**: `POST /api/v2/transactions/presign/`  
**Authentication**: Required  
**Subscription**: Required

Generates a presigned URL for uploading files to S3.

**Request Body:**
```json
{
  "content_type": "image/jpeg",
  "extension": "jpg",
  "key": "transaction_receipt"
}
```

**Allowed Keys:**
- `transaction_receipt` - For transaction receipts
- `profile_picture` - For user profile pictures

**Success Response** (200):
```json
{
  "upload_url": "https://bucket.s3.amazonaws.com/receipts/...",
  "object_key": "receipts/transaction-123/receipt-456.jpg",
  "expires_in": 300
}
```

**Error Responses:**

Invalid key (400):
```json
{
  "error": "Invalid S3 key prefix."
}
```

No subscription (403):
```json
{
  "error": "Valid subscription required."
}
```

**Usage Flow:**
1. Request presigned URL from backend
2. Upload file directly to S3 using presigned URL
3. Save `object_key` in transaction or user profile
4. Display images using presigned view URLs

**Example:**
```javascript
// Step 1: Get presigned URL
const response = await fetch('/api/v2/transactions/presign/', {
  method: 'POST',
  credentials: 'include',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    content_type: file.type,
    extension: file.name.split('.').pop(),
    key: 'transaction_receipt'
  })
});
const { upload_url, object_key } = await response.json();

// Step 2: Upload to S3
await fetch(upload_url, {
  method: 'PUT',
  body: file,
  headers: { 'Content-Type': file.type }
});

// Step 3: Save object_key in transaction
await fetch('/api/v2/transactions/', {
  method: 'POST',
  credentials: 'include',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    amount: '500.00',
    description: 'Receipt uploaded',
    transaction_type: 'debit',
    date: '2025-11-16',
    register: 1,
    image_keys: [object_key]
  })
});
```

---

### 22. Cleanup Unused S3 Objects

**Endpoint**: `POST /api/v2/transactions/cleanup/`  
**Authentication**: Required

Deletes S3 objects that are no longer referenced.

**Request Body:**
```json
{
  "keys": [
    "receipts/transaction-123/old-receipt.jpg",
    "receipts/transaction-456/deleted.jpg"
  ]
}
```

**Success Response** (200):
```json
{
  "status": "success",
  "deleted": 2,
  "keys": [
    "receipts/transaction-123/old-receipt.jpg",
    "receipts/transaction-456/deleted.jpg"
  ]
}
```

**Usage:**
- Clean up after replacing images
- Remove images from cancelled uploads
- Maintain S3 storage hygiene

---

## Register Management

### 23. List Registers

**Endpoint**: `GET /api/v2/registers/`  
**Authentication**: Required

Retrieves user's registers (categories).

**Success Response** (200):
```json
{
  "results": [
    {
      "id": 1,
      "name": "Cash",
      "description": "Cash transactions",
      "debit": true,
      "credit": true,
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-01T00:00:00Z"
    },
    {
      "id": 2,
      "name": "Bank",
      "description": "Bank account",
      "debit": true,
      "credit": true,
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

**Notes:**
- Ordered by created_at (desc)
- Response cached for 10 minutes
- `debit: true` - Register allows debit transactions
- `credit: true` - Register allows credit transactions

---

### 24. Create Register

**Endpoint**: `POST /api/v2/registers/`  
**Authentication**: Required  
**Subscription**: Required

Creates a new register.

**Request Body:**
```json
{
  "name": "Credit Card",
  "description": "Credit card expenses",
  "debit": true,
  "credit": false
}
```

**Success Response** (201):
```json
{
  "id": 3,
  "name": "Credit Card",
  "description": "Credit card expenses",
  "debit": true,
  "credit": false,
  "created_at": "2025-11-16T10:30:00Z",
  "updated_at": "2025-11-16T10:30:00Z"
}
```

**Error Responses:**

Duplicate name (400):
```json
{
  "status": false,
  "message": "Register with this name already exists."
}
```

No subscription (403):
```json
{
  "status": false,
  "message": "Valid subscription required for this operation"
}
```

**Notes:**
- Name is case-insensitive unique per user
- At least one of `debit` or `credit` must be true
- Invalidates register cache

---

### 25. Update Register

**Endpoint**: `PUT /api/v2/registers/{id}/` or `PATCH /api/v2/registers/{id}/`  
**Authentication**: Required  
**Subscription**: Required

Updates an existing register.

**Request Body:**
```json
{
  "name": "Business Credit Card",
  "description": "Updated description",
  "debit": true,
  "credit": false
}
```

**Success Response** (200):
```json
{
  "id": 3,
  "name": "Business Credit Card",
  "description": "Updated description",
  "debit": true,
  "credit": false
}
```

**Error Responses:**

Cannot disable transaction type (400):
```json
{
  "status": false,
  "message": "Cannot change register. There are existing debit transactions associated with this register."
}
```

No changes (400):
```json
{
  "status": false,
  "message": "No changes detected."
}
```

**Notes:**
- Cannot disable `debit` if debit transactions exist
- Cannot disable `credit` if credit transactions exist
- Cannot change name to duplicate (case-insensitive)
- At least one of `debit` or `credit` must remain true

---

### 26. Delete Register

**Endpoint**: `DELETE /api/v2/registers/{id}/`  
**Authentication**: Required  
**Subscription**: Required

Deletes a register.

**Success Response** (204):
```
No content
```

**Error Response** (400):
```json
{
  "status": false,
  "message": "Cannot delete register with existing transactions."
}
```

**Notes:**
- Can only delete registers with no transactions
- First delete all associated transactions
- Invalidates register cache

---

## Holiday Management

### 27. List Holidays

**Endpoint**: `GET /api/v2/holiday/`  
**Authentication**: Required

Retrieves holidays with optional filtering.

**Query Parameters:**
- `date` - Specific date
- `start_date` - From date
- `end_date` - To date

**Request Examples:**
```
GET /api/v2/holiday/
GET /api/v2/holiday/?start_date=2025-01-01&end_date=2025-12-31
GET /api/v2/holiday/?date=2025-12-25
```

**Success Response** (200):
```json
{
  "status": true,
  "message": "Holidays fetched successfully.",
  "data": [
    {
      "id": 1,
      "date": "2025-12-25",
      "is_holiday": true,
      "holiday_reason": "Christmas Day"
    },
    {
      "id": 2,
      "date": "2025-01-01",
      "is_holiday": true,
      "holiday_reason": "New Year"
    }
  ]
}
```

**Empty Response** (200):
```json
{
  "status": true,
  "message": "No holidays available.",
  "data": []
}
```

**Notes:**
- Returns holidays ordered by date
- Sundays are automatically holidays (not listed unless explicitly marked)
- Empty result is not an error

---

### 28. Mark Holiday

**Endpoint**: `POST /api/v2/holiday/`  
**Authentication**: Required

Marks a date as a holiday.

**Request Body:**
```json
{
  "date": "2025-12-25",
  "reason": "Christmas Day"
}
```

**Success Response** (201 or 200):
```json
{
  "status": true,
  "message": "Holiday marked on 2025-12-25."
}
```

**Error Responses:**

Sunday (400):
```json
{
  "status": false,
  "message": "Cannot mark a holiday on a Sunday."
}
```

Already holiday (500):
```json
{
  "status": false,
  "message": "Already marked as holiday"
}
```

Has transactions (404):
```json
{
  "status": false,
  "message": "Cannot mark holiday on 2025-12-25, transactions already exist."
}
```

**Notes:**
- Cannot mark Sundays (already holidays)
- Cannot mark dates with existing transactions
- Can mark future dates
- Can mark past dates if no transactions exist

---

### 29. Remove Holiday

**Endpoint**: `DELETE /api/v2/holiday/`  
**Authentication**: Required

Removes holiday marking from a date.

**Request Body:**
```json
{
  "date": "2025-12-25"
}
```

**Success Response** (200):
```json
{
  "status": true,
  "message": "Holiday removed for 2025-12-25."
}
```

**Error Responses:**

No holiday found (404):
```json
{
  "status": false,
  "message": "No holiday found for 2025-12-25."
}
```

Cannot remove Sunday (400):
```json
{
  "status": false,
  "message": "Cannot remove holiday for 2025-12-24 as it is a Sunday."
}
```

**Notes:**
- Future holiday journals are deleted entirely
- Past holiday journals have `is_holiday` set to false
- Cannot remove Sunday holidays

---

## Payment Management

### 30. List Subscription Plans

**Endpoint**: `GET /api/v2/payment/plans/`  
**Authentication**: Not required

Retrieves all available subscription plans.

**Success Response** (200):
```json
{
  "message": "All available plans retrieved successfully",
  "plans": [
    {
      "id": 1,
      "name": "Monthly Plan",
      "plan_id": "plan_monthly_2025",
      "price": 99,
      "duration_days": 0,
      "duration_months": 1,
      "duration_years": 0,
      "savings": 0,
      "description": "1 month subscription"
    },
    {
      "id": 2,
      "name": "Yearly Plan",
      "plan_id": "plan_yearly_2025",
      "price": 999,
      "duration_days": 0,
      "duration_months": 0,
      "duration_years": 1,
      "savings": 189,
      "description": "1 year subscription - Save 189 INR"
    }
  ]
}
```

**Notes:**
- Public endpoint (no authentication needed)
- Price in INR (Indian Rupees)
- Savings show discount compared to monthly plan

---

### 31. Get Plan Details

**Endpoint**: `GET /api/v2/payment/plan/{id}/`  
**Authentication**: Not required

Retrieves details of a specific plan.

**Success Response** (200):
```json
{
  "message": "Plan details retrieved successfully",
  "plan": {
    "id": 2,
    "name": "Yearly Plan",
    "plan_id": "plan_yearly_2025",
    "price": 999,
    "duration_days": 0,
    "duration_months": 0,
    "duration_years": 1,
    "savings": 189,
    "description": "1 year subscription - Save 189 INR"
  }
}
```

**Error Response** (404):
```json
{
  "detail": "Not found."
}
```

---

### 32. Create Payment Order

**Endpoint**: `GET /api/v2/payment/order/{planId}/`  
**Authentication**: Required

Creates a Razorpay order for subscription payment.

**Success Response** (201):
```json
{
  "message": "Order created",
  "order": {
    "id": 1,
    "order_id": "order_MhYxO2qK8zJxJo",
    "amount": 999,
    "currency": "INR",
    "name": "Yearly Plan",
    "key": "rzp_test_xxxxx",
    "description": "1 year subscription - Save 189 INR"
  }
}
```

**Error Response** (500):
```json
{
  "message": "Failed to create razorpay order",
  "error": "Error details"
}
```

**Notes:**
- Amount is automatically discounted if user has unused referral code
- Order expires after 1 hour
- `key` is Razorpay public key for frontend integration
- `order_id` is used for payment verification

**Usage Flow:**
1. User selects plan
2. Frontend calls this endpoint to create order
3. Frontend opens Razorpay payment modal with order details
4. User completes payment
5. Razorpay redirects with payment details
6. Frontend calls `/verify/` to complete payment

---

### 33. Verify Payment

**Endpoint**: `POST /api/v2/payment/verify/`  
**Authentication**: Required

Verifies Razorpay payment and activates subscription.

**Request Body:**
```json
{
  "razorpay_payment_id": "pay_MhYxTjKdO2qK8z",
  "razorpay_order_id": "order_MhYxO2qK8zJxJo",
  "razorpay_signature": "abc123def456..."
}
```

**Success Response** (200):
```json
{
  "message": "Payment verified and order updated",
  "order_id": 1
}
```

**Error Responses:**

Missing fields (400):
```json
{
  "message": "Missing payment verification fields"
}
```

Signature verification failed (400):
```json
{
  "message": "Signature verification failed",
  "error": "Error details"
}
```

Order not found (404):
```json
{
  "message": "Order not found for given razorpay_order_id"
}
```

**Notes:**
- Verifies payment signature with Razorpay
- Updates order status to 'paid'
- Activates or extends user subscription
- Marks referral code as used (if applicable)
- Subscription starts today if first purchase
- Subscription extends from current end date if renewal

---

### 34. Payment History

**Endpoint**: `GET /api/v2/payment/history/`  
**Authentication**: Required

Retrieves user's payment history.

**Success Response** (200):
```json
{
  "message": "Payment history retrieved successfully",
  "history": [
    {
      "id": 1,
      "order_id": "order_MhYxO2qK8zJxJo",
      "amount": 999,
      "status": "paid",
      "expired": false,
      "currency": "INR",
      "razorpay_order_id": "order_MhYxO2qK8zJxJo",
      "razorpay_payment_id": "pay_MhYxTjKdO2qK8z",
      "created_at": "2025-11-16T10:30:00Z"
    }
  ]
}
```

**Notes:**
- Ordered by created_at (desc)
- Shows all orders (created, paid, failed, expired)

---

### 35. Check Payment Status

**Endpoint**: `GET /api/v2/payment/status/{id}/`  
**Authentication**: Required

Checks status of a payment order.

**Success Response** (200):
```json
{
  "message": "Payment status retrieved",
  "payment": {
    "id": 1,
    "order_id": "order_MhYxO2qK8zJxJo",
    "status": "paid",
    "amount": 999,
    "currency": "INR",
    "razorpay_order_id": "order_MhYxO2qK8zJxJo",
    "razorpay_payment_id": "pay_MhYxTjKdO2qK8z"
  }
}
```

**Error Responses:**

Not authorized (403):
```json
{
  "message": "Not authorized to view this payment"
}
```

Order expired (400):
```json
{
  "message": "Order has expired"
}
```

**Notes:**
- Syncs status with Razorpay if different locally
- Orders expire after 1 hour
- Can only view own orders

---

### 36. Retry Payment

**Endpoint**: `GET /api/v2/payment/retry/{orderId}/`  
**Authentication**: Required

Retrieves order details to retry a failed payment.

**Success Response** (200):
```json
{
  "message": "Retry initiated",
  "order": {
    "id": 1,
    "order_id": "order_MhYxO2qK8zJxJo",
    "amount": 999,
    "currency": "INR",
    "name": "Yearly Plan",
    "key": "rzp_test_xxxxx",
    "description": "1 year subscription"
  }
}
```

**Error Responses:**

Not authorized (403):
```json
{
  "message": "Not authorized to retry this payment"
}
```

Order expired (400):
```json
{
  "message": "Order has expired, cannot retry payment"
}
```

**Notes:**
- Can retry payments for orders that failed
- Cannot retry expired orders (> 1 hour old)
- Returns same order details for Razorpay integration

---

*[End of Part 2]*
