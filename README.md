# BO Journal Backend

A comprehensive Django REST API for managing journals, transactions, registers, and payments with integrated authentication, email services, and background task processing.

## 📚 Documentation

All documentation has been consolidated for easy reference:

### API Documentation (For Frontend Developers)

Complete API reference with request/response examples:

1. **[COMPLETE_API_DOCUMENTATION.md](COMPLETE_API_DOCUMENTATION.md)** - Part 1
   - Introduction & Setup
   - Authentication (JWT with HTTP-only cookies)
   - Common Response Patterns
   - Authentication Endpoints (10 endpoints)
   - User Management (2 endpoints)

2. **[API_DOCUMENTATION_PART2.md](API_DOCUMENTATION_PART2.md)** - Part 2
   - Journal Management (3 endpoints)
   - Transaction Management (7 endpoints)
   - Register Management (5 endpoints)
   - Holiday Management (3 endpoints)
   - Payment Management (6 endpoints)

3. **[API_DOCUMENTATION_PART3.md](API_DOCUMENTATION_PART3.md)** - Part 3
   - Authentication Flows (Signup, Login, Password Reset, Token Refresh)
   - Common Use Cases with Complete Code Examples
   - Error Handling Guide
   - Rate Limiting
   - API Best Practices
   - Testing Instructions
   - Security Considerations

**Total**: 36 API endpoints fully documented with examples

### Production Deployment (For DevOps)

Complete AWS EC2 Ubuntu deployment guide:

1. **[PRODUCTION_DEPLOYMENT_GUIDE.md](PRODUCTION_DEPLOYMENT_GUIDE.md)** - Part 1
   - Prerequisites (AWS EC2, Domain, External Services)
   - Initial Server Setup
   - System Dependencies
   - PostgreSQL Setup (RDS + Local)
   - Redis Setup (ElastiCache + Local)
   - Application Deployment
   - Gunicorn Configuration
   - Nginx Configuration
   - SSL/TLS with Let's Encrypt
   - Celery Configuration

2. **[PRODUCTION_DEPLOYMENT_GUIDE_PART2.md](PRODUCTION_DEPLOYMENT_GUIDE_PART2.md)** - Part 2
   - Environment Configuration
   - Security Hardening (Fail2Ban, Automatic Updates)
   - Monitoring & Logging
   - Backup Strategy
   - Maintenance Procedures
   - Troubleshooting Guide
   - Performance Optimization
   - Security Checklist

### Configuration

- **[django_backend/example.env](django_backend/example.env)** - Environment variables template with detailed comments
- **[SETTINGS_USAGE_GUIDE.md](SETTINGS_USAGE_GUIDE.md)** - How to use environment-specific settings
- **[requirements/README.md](requirements/README.md)** - Dependencies management guide

## 🚀 Quick Start

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd bo-journal-backend/backend
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv env
   source env/bin/activate  # Linux/Mac
   # or
   env\Scripts\activate  # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements/development.txt
   ```

4. **Configure environment**
   ```bash
   cd django_backend
   cp example.env .env
   # Edit .env file with your settings
   nano .env
   ```

5. **Set environment**
   ```bash
   # In .env file
   DJANGO_ENVIRONMENT=development
   ```

6. **Run migrations**
   ```bash
   python manage.py migrate
   ```

7. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

8. **Run development server**
   ```bash
   python manage.py runserver
   ```

9. **Start Celery (in another terminal)**
   ```bash
   source env/bin/activate
   cd django_backend
   celery -A django_backend worker -l info
   ```

10. **Start Celery Beat (in another terminal)**
    ```bash
    source env/bin/activate
    cd django_backend
    celery -A django_backend beat -l info
    ```

The API will be available at `http://localhost:8000/api/v2/`

## 🔑 Key Features

- **Authentication**: JWT-based with HTTP-only cookies
- **Email Service**: OTP verification, password reset, welcome emails
- **Journal Management**: Track daily financial journals with opening balances
- **Transaction Management**: CRUD operations with S3 image uploads
- **Register Management**: Categorize transactions
- **Holiday Management**: Mark non-working days
- **Payment Integration**: Razorpay subscription management
- **Background Tasks**: Celery for async email sending
- **Caching**: Redis for performance optimization
- **Rate Limiting**: Prevent abuse with throttling

## 📦 Tech Stack

- **Framework**: Django 5.1.3 + Django REST Framework
- **Database**: PostgreSQL
- **Cache**: Redis
- **Task Queue**: Celery with Redis broker
- **Storage**: AWS S3
- **Payment**: Razorpay
- **Authentication**: JWT (djangorestframework-simplejwt)
- **Web Server**: Gunicorn + Nginx (production)

## 🧪 Testing

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test authapp
python manage.py test journal
python manage.py test transactions
```

## 📁 Project Structure

```
backend/
├── django_backend/           # Main Django project
│   ├── settings/             # Environment-specific settings
│   │   ├── base.py           # Common settings
│   │   ├── development.py    # Dev settings
│   │   ├── testing.py        # Test settings
│   │   └── production.py     # Production settings
│   ├── celery.py             # Celery configuration
│   ├── urls.py               # Main URL routing
│   └── example.env           # Environment template
│
├── authapp/                  # Authentication & user management
├── emailservice/             # Email sending & templates
├── journal/                  # Journal management
├── transactions/             # Transaction CRUD
├── registers/                # Register management
├── holiday/                  # Holiday marking
├── payment/                  # Razorpay integration
├── core/                     # Shared utilities
│   ├── authentication.py     # JWT auth backend
│   ├── permissions.py        # Custom permissions
│   ├── throttling.py         # Rate limiting
│   └── s3_utils.py           # S3 helpers
│
└── requirements/             # Dependencies
    ├── base.txt              # Common packages
    ├── development.txt       # Dev packages
    ├── testing.txt           # Test packages
    └── production.txt        # Production packages
```

## 🌍 Environment Configuration

The project uses environment-specific settings:

- **Development**: `DJANGO_ENVIRONMENT=development`
- **Testing**: `DJANGO_ENVIRONMENT=testing`
- **Production**: `DJANGO_ENVIRONMENT=production`

See [SETTINGS_USAGE_GUIDE.md](SETTINGS_USAGE_GUIDE.md) for detailed instructions.

## 🔒 Security

- JWT tokens in HTTP-only cookies (XSS protection)
- CSRF protection enabled
- CORS configured for specific origins
- Rate limiting on authentication endpoints
- Secure headers in production
- Environment variables for sensitive data

## 📞 API Base URL

- **Development**: `http://localhost:8000/api/v2/`
- **Production**: `https://your-domain.com/api/v2/`

## 📖 API Endpoints Overview

See the complete documentation files for details:

**Authentication** (10 endpoints):
- POST `/auth/signup` - Create account
- POST `/auth/verify` - Verify OTP
- POST `/auth/login` - Login
- POST `/auth/logout` - Logout
- POST `/auth/refresh` - Refresh token
- GET `/auth/check` - Check auth status
- POST `/auth/resetpassword` - Request password reset
- POST `/auth/updatepassword` - Update password
- GET `/auth/csrf` - Get CSRF token
- GET `/auth/health` - Health check

**User Management** (2 endpoints):
- PATCH `/user/update` - Update profile
- GET `/user/profile-picture-url` - Get profile picture URL

**Journal Management** (3 endpoints):
- GET `/journal` - List journals
- POST `/journal/create-first-entry` - Create first journal
- PATCH `/journal/update-opening-balance` - Update opening balance

**Transaction Management** (7 endpoints):
- GET `/transactions` - List transactions
- POST `/transactions` - Create transaction
- GET `/transactions/{id}` - Get transaction
- PUT `/transactions/{id}` - Update transaction
- DELETE `/transactions/{id}` - Delete transaction
- POST `/transactions/presigned-url` - Get S3 upload URL
- DELETE `/transactions/cleanup-unused-s3-objects` - Cleanup orphaned files

**Register Management** (5 endpoints):
- GET `/registers` - List registers
- POST `/registers` - Create register
- GET `/registers/{id}` - Get register
- PUT `/registers/{id}` - Update register
- DELETE `/registers/{id}` - Delete register

**Holiday Management** (3 endpoints):
- GET `/holiday` - List holidays
- POST `/holiday` - Mark holiday
- DELETE `/holiday` - Remove holiday

**Payment Management** (6 endpoints):
- GET `/payment/plans` - List subscription plans
- GET `/payment/plan/{plan_id}` - Get plan details
- POST `/payment/create-order` - Create Razorpay order
- POST `/payment/verify` - Verify payment
- GET `/payment/history` - Get payment history
- GET `/payment/status` - Check subscription status

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Write/update tests
4. Update documentation
5. Submit a pull request

## 📝 License

[Your License Here]

## 👥 Team

[Your Team Information]

---

**For detailed API usage, see the documentation files in this directory.**
