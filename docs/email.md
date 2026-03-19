# Email Service (Namecheap SMTP) — Setup & Usage

This document describes how to configure the project's email sending system using Namecheap Private Email SMTP, with Celery+Redis queues and optional SendGrid fallback.

Environment variables

- SMTP_USERNAME: SMTP user (e.g. no-reply@yourdomain.com)
- SMTP_PASSWORD: SMTP password
- SMTP_HOST: mail.privateemail.com (default)
- SMTP_PORT: 587 (default)
- EMAIL_FROM: Optional override for From header
- SUPPORT_EMAIL: Optional Reply-To
- CELERY_BROKER_URL: redis://... (project also reads CELERY_BROKER_URL)
- CELERY_RESULT_BACKEND: redis://...
- SG_API_KEY: Optional SendGrid API key for fallback
- SG_SMTP_USER / SG_SMTP_PASS: Optional SendGrid SMTP relay creds
- RATE_CRITICAL / RATE_STANDARD / RATE_BULK: rate limit strings (optional)

Running workers

Run dedicated workers for each queue (example):

```bash
celery -A django_backend worker -Q critical -n worker_critical@%h --concurrency=4
celery -A django_backend worker -Q standard -n worker_standard@%h --concurrency=4
celery -A django_backend worker -Q bulk -n worker_bulk@%h --concurrency=2
```

Deliverability checklist (Namecheap Private Email)

- MX records: set as provided by Namecheap for your domain
- SPF: add `v=spf1 include:spf.privateemail.com -all`
- DKIM: enable in Namecheap control panel and publish the TXT record they give
- DMARC: start with `v=DMARC1; p=none; rua=mailto:dmarc@yourdomain.com` then tighten
- PTR/Reverse DNS: ensure your sending infrastructure has correct PTR if self-hosted

Seeding templates

Create `EmailTemplate` entries for `otp`, `welcome`, `subscription_update`, `subscription_expiry`. Admin panel enforces only one published template per key+locale.

Admin endpoints

- `POST /api/emailservice/admin/otp/` (admin-only)
- `POST /api/emailservice/admin/welcome/`
- `POST /api/emailservice/admin/subscription-update/`
- `POST /api/emailservice/admin/subscription-expiry/`

Each endpoint expects JSON: `{ "to_email": "user@example.com", "data": {"otp": "123456"} }` (OTP endpoint requires `otp` field).
