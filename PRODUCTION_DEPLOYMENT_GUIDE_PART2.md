# BO Journal - Production Deployment Guide (Part 2)

## Environment Configuration

### Complete .env File for Production

Create `/home/bojournal/bo-journal-backend/backend/django_backend/.env`:

```bash
# ===================================
# PRODUCTION ENVIRONMENT CONFIGURATION
# ===================================

# Django Environment
DJANGO_ENVIRONMENT=production
PRODUCTION=True

# Django Secret Key (CRITICAL - Generate unique key)
# Generate with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
SECRET_KEY=your-production-secret-key-change-this-to-random-string

# Database Configuration (PostgreSQL)
DB_USER=bojournal_user
DB_PASSWORD=your_secure_database_password
DB_HOST=your-rds-endpoint.amazonaws.com  # Or localhost
DB_PORT=5432
DB_NAME=bo_journal

# Redis Configuration
REDIS_LOCATION=redis://your-elasticache-endpoint:6379/1  # Or redis://127.0.0.1:6379/1

# Email Configuration (SMTP)
EMAIL_HOST=smtp.gmail.com  # Or your SMTP provider
EMAIL_PORT=587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-specific-password

# JWT Configuration
JWT_SECRET=your-jwt-secret-key-different-from-django-secret

# CORS & CSRF Configuration
ORIGIN0=https://your-frontend-domain.com
ORIGIN1=https://www.your-frontend-domain.com
HOST0=your-api-domain.com

# AWS S3 Configuration
S3_REGION=ap-south-1
S3_ACCESS_KEY=your-aws-access-key
S3_SECRET_ACCESS_KEY=your-aws-secret-access-key
S3_BUCKET_NAME=your-bucket-name
AWS_PRESIGNED_URL_EXPIRES=600

# Timezone
TIMEZONE=Asia/Kolkata

# Razorpay (Use LIVE keys for production)
RAZORPAY_KEY=rzp_live_your_key_here
RAZORPAY_SECRET=your_live_razorpay_secret
```

### Secure .env File

```bash
# Set proper permissions
sudo chown bojournal:bojournal /home/bojournal/bo-journal-backend/backend/django_backend/.env
sudo chmod 600 /home/bojournal/bo-journal-backend/backend/django_backend/.env

# Verify permissions
ls -la /home/bojournal/bo-journal-backend/backend/django_backend/.env
# Should show: -rw------- 1 bojournal bojournal
```

---

## Security Hardening

### 1. Fail2Ban Setup

Protect against brute force attacks:

```bash
# Install Fail2Ban
sudo apt install -y fail2ban

# Create custom configuration
sudo nano /etc/fail2ban/jail.local
```

**jail.local:**
```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
destemail = your-email@example.com
sendername = Fail2Ban
action = %(action_mwl)s

[sshd]
enabled = true
port = 22
logpath = /var/log/auth.log

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
```

```bash
# Start and enable Fail2Ban
sudo systemctl start fail2ban
sudo systemctl enable fail2ban

# Check status
sudo fail2ban-client status
```

### 2. Automatic Security Updates

```bash
# Install unattended-upgrades
sudo apt install -y unattended-upgrades

# Configure
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

### 3. Disable Unnecessary Services

```bash
# List all services
systemctl list-unit-files --type=service --state=enabled

# Disable unused services (example)
sudo systemctl disable bluetooth.service
sudo systemctl disable cups.service
```

### 4. Configure Django Security Settings

Verify these are set in `settings/production.py`:

```python
# Security settings (already configured in production.py)
DEBUG = False
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
```

### 5. Rate Limiting in Nginx

Add to Nginx configuration:

```bash
sudo nano /etc/nginx/sites-available/bojournal
```

Add at the top (before server block):

```nginx
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=10r/m;
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;

server {
    # ... existing config ...
    
    # Rate limit authentication endpoints
    location ~ ^/api/v2/auth/(login|signup|resetpassword) {
        limit_req zone=auth_limit burst=5 nodelay;
        proxy_pass http://gunicorn;
        # ... other proxy settings ...
    }
    
    # Rate limit other API endpoints
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://gunicorn;
        # ... other proxy settings ...
    }
}
```

```bash
# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

---

## Monitoring & Logging

### 1. Configure Django Logging

Already configured in `settings/production.py`. Logs go to `/var/log/django/`.

Create log directory:

```bash
sudo mkdir -p /var/log/django
sudo chown bojournal:bojournal /var/log/django
```

### 2. Log Rotation

```bash
sudo nano /etc/logrotate.d/bojournal
```

**/etc/logrotate.d/bojournal:**
```
/var/log/django/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 bojournal bojournal
    sharedscripts
    postrotate
        systemctl reload gunicorn > /dev/null 2>&1 || true
    endscript
}

/var/log/gunicorn/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 bojournal bojournal
    sharedscripts
    postrotate
        systemctl reload gunicorn > /dev/null 2>&1 || true
    endscript
}

/var/log/celery/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 bojournal bojournal
    sharedscripts
    postrotate
        systemctl restart celery celerybeat > /dev/null 2>&1 || true
    endscript
}

/var/log/nginx/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        systemctl reload nginx > /dev/null 2>&1 || true
    endscript
}
```

```bash
# Test logrotate
sudo logrotate -d /etc/logrotate.d/bojournal
```

### 3. System Monitoring Script

Create monitoring script:

```bash
sudo nano /usr/local/bin/monitor-bojournal.sh
```

**/usr/local/bin/monitor-bojournal.sh:**
```bash
#!/bin/bash

# BO Journal Monitoring Script

EMAIL="admin@example.com"
SERVICES=("gunicorn" "celery" "celerybeat" "nginx" "postgresql" "redis")

check_service() {
    if ! systemctl is-active --quiet "$1"; then
        echo "Service $1 is down! Attempting restart..." | mail -s "BO Journal Alert: $1 Down" $EMAIL
        systemctl start "$1"
    fi
}

check_disk_space() {
    DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -gt 80 ]; then
        echo "Disk usage is at ${DISK_USAGE}%!" | mail -s "BO Journal Alert: High Disk Usage" $EMAIL
    fi
}

check_memory() {
    MEM_USAGE=$(free | awk 'NR==2 {printf "%.0f", $3/$2 * 100}')
    if [ "$MEM_USAGE" -gt 90 ]; then
        echo "Memory usage is at ${MEM_USAGE}%!" | mail -s "BO Journal Alert: High Memory Usage" $EMAIL
    fi
}

# Check all services
for service in "${SERVICES[@]}"; do
    check_service "$service"
done

# Check resources
check_disk_space
check_memory

# Check application health
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/v2/auth/health)
if [ "$HTTP_CODE" -ne 200 ]; then
    echo "Health check failed with HTTP $HTTP_CODE" | mail -s "BO Journal Alert: Health Check Failed" $EMAIL
fi
```

```bash
# Make executable
sudo chmod +x /usr/local/bin/monitor-bojournal.sh

# Add to crontab (run every 5 minutes)
sudo crontab -e
```

Add:
```
*/5 * * * * /usr/local/bin/monitor-bojournal.sh
```

### 4. View Logs

```bash
# Django logs
sudo tail -f /var/log/django/django.log

# Gunicorn logs
sudo tail -f /var/log/gunicorn/error.log
sudo tail -f /var/log/gunicorn/access.log

# Celery logs
sudo tail -f /var/log/celery/worker.log
sudo tail -f /var/log/celery/beat.log

# Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/bojournal_access.log

# System logs
sudo journalctl -u gunicorn -f
sudo journalctl -u celery -f
```

---

## Backup Strategy

### 1. Database Backup Script

```bash
sudo nano /usr/local/bin/backup-database.sh
```

**/usr/local/bin/backup-database.sh:**
```bash
#!/bin/bash

# Configuration
BACKUP_DIR="/home/bojournal/backups/database"
DB_NAME="bo_journal"
DB_USER="bojournal_user"
DB_PASSWORD="your_password"
DB_HOST="localhost"
RETENTION_DAYS=7

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup filename with timestamp
BACKUP_FILE="$BACKUP_DIR/bo_journal_$(date +%Y%m%d_%H%M%S).sql.gz"

# Perform backup
PGPASSWORD=$DB_PASSWORD pg_dump -h $DB_HOST -U $DB_USER $DB_NAME | gzip > $BACKUP_FILE

# Remove old backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Database backup completed: $BACKUP_FILE"
```

```bash
# Make executable
sudo chmod +x /usr/local/bin/backup-database.sh

# Add to crontab (daily at 2 AM)
sudo crontab -e
```

Add:
```
0 2 * * * /usr/local/bin/backup-database.sh
```

### 2. Upload Backups to S3 (Optional)

```bash
# Install AWS CLI
sudo apt install -y awscli

# Configure AWS credentials
aws configure
```

Update backup script to upload to S3:

```bash
# Add after backup creation
aws s3 cp $BACKUP_FILE s3://your-backup-bucket/database/
```

### 3. Application Code Backup

```bash
# Backup script for application code
sudo nano /usr/local/bin/backup-code.sh
```

```bash
#!/bin/bash

BACKUP_DIR="/home/bojournal/backups/code"
APP_DIR="/home/bojournal/bo-journal-backend"

mkdir -p $BACKUP_DIR

# Create backup
tar -czf $BACKUP_DIR/code_$(date +%Y%m%d).tar.gz -C $APP_DIR .

# Remove old backups (keep 7 days)
find $BACKUP_DIR -name "code_*.tar.gz" -mtime +7 -delete
```

```bash
sudo chmod +x /usr/local/bin/backup-code.sh
```

### 4. Restore from Backup

**Database Restore:**
```bash
# Decompress and restore
gunzip < /path/to/backup.sql.gz | psql -h localhost -U bojournal_user bo_journal
```

**Code Restore:**
```bash
# Extract backup
cd /home/bojournal
tar -xzf /path/to/backup.tar.gz
```

---

## Maintenance

### 1. Update Application

```bash
# Switch to application user
sudo su - bojournal

# Navigate to project
cd /home/bojournal/bo-journal-backend

# Activate virtual environment
source backend/env/bin/activate

# Pull latest code
git pull origin main

# Install new dependencies
pip install -r backend/requirements/production.txt

# Navigate to django project
cd backend/django_backend

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Exit to root
exit

# Restart services
sudo systemctl restart gunicorn celery celerybeat
```

### 2. Update System Packages

```bash
# Update package list
sudo apt update

# Upgrade packages
sudo apt upgrade -y

# Remove unnecessary packages
sudo apt autoremove -y

# Reboot if kernel updated
sudo reboot
```

### 3. Renew SSL Certificate

```bash
# Certbot handles this automatically
# To manually renew:
sudo certbot renew

# Reload Nginx
sudo systemctl reload nginx
```

### 4. Clean Up Old Logs

```bash
# Clean old Django logs
sudo find /var/log/django -name "*.log.*" -mtime +30 -delete

# Clean old Gunicorn logs
sudo find /var/log/gunicorn -name "*.log.*" -mtime +30 -delete

# Clean old Celery logs
sudo find /var/log/celery -name "*.log.*" -mtime +30 -delete
```

### 5. Database Maintenance

```bash
# Vacuum database (as postgres user)
sudo -u postgres psql bo_journal -c "VACUUM ANALYZE;"

# Check database size
sudo -u postgres psql bo_journal -c "SELECT pg_size_pretty(pg_database_size('bo_journal'));"
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Gunicorn Won't Start

**Check logs:**
```bash
sudo journalctl -u gunicorn -n 50
```

**Common causes:**
- Syntax error in code
- Missing dependencies
- Wrong file permissions
- Environment variable not set

**Solution:**
```bash
# Test manually
sudo su - bojournal
source backend/env/bin/activate
cd backend/django_backend
gunicorn --bind 0.0.0.0:8000 django_backend.wsgi:application
```

#### 2. 502 Bad Gateway

**Cause:** Gunicorn not running or socket issue

**Solution:**
```bash
# Check Gunicorn status
sudo systemctl status gunicorn

# Check socket
sudo systemctl status gunicorn.socket

# Restart
sudo systemctl restart gunicorn
```

#### 3. Static Files Not Loading

**Solution:**
```bash
# Recollect static files
sudo su - bojournal
cd /home/bojournal/bo-journal-backend/backend/django_backend
source ../../env/bin/activate
python manage.py collectstatic --noinput

# Check Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

#### 4. Database Connection Error

**Check database status:**
```bash
sudo systemctl status postgresql
```

**Test connection:**
```bash
psql -h localhost -U bojournal_user -d bo_journal
```

**Check credentials in .env file**

#### 5. Celery Not Processing Tasks

**Check worker status:**
```bash
sudo systemctl status celery
sudo tail -f /var/log/celery/worker.log
```

**Check Redis connection:**
```bash
redis-cli ping
```

**Restart Celery:**
```bash
sudo systemctl restart celery celerybeat
```

#### 6. High Memory Usage

**Check processes:**
```bash
top
htop  # If installed
```

**Check Django processes:**
```bash
ps aux | grep gunicorn
ps aux | grep celery
```

**Solution:**
- Reduce Gunicorn workers (edit gunicorn.service)
- Restart services
- Consider upgrading instance type

#### 7. SSL Certificate Issues

**Check certificate:**
```bash
sudo certbot certificates
```

**Renew certificate:**
```bash
sudo certbot renew --force-renewal
sudo systemctl reload nginx
```

#### 8. Permission Denied Errors

**Fix file permissions:**
```bash
# Application files
sudo chown -R bojournal:bojournal /home/bojournal/bo-journal-backend

# Log files
sudo chown -R bojournal:bojournal /var/log/django
sudo chown -R bojournal:bojournal /var/log/gunicorn
sudo chown -R bojournal:bojournal /var/log/celery
```

#### 9. CORS Errors

**Check Nginx configuration:**
```bash
sudo nano /etc/nginx/sites-available/bojournal
```

**Ensure proxy headers are set:**
```nginx
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header Host $http_host;
```

**Check Django settings:**
- Verify `ORIGIN0`, `ORIGIN1` in .env
- Check `ALLOWED_HOSTS` in settings/production.py

#### 10. Rate Limiting Too Strict

**Adjust Nginx rate limits:**
```bash
sudo nano /etc/nginx/sites-available/bojournal
```

Increase rates:
```nginx
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=20r/m;  # Increased from 10r/m
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=200r/m;  # Increased from 100r/m
```

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## Performance Optimization

### 1. Database Query Optimization

Enable query logging in production.py (temporarily):

```python
LOGGING['loggers']['django.db.backends'] = {
    'level': 'DEBUG',
    'handlers': ['file'],
}
```

Analyze slow queries and add indexes.

### 2. Redis Caching

Already implemented. Monitor cache hit rate:

```python
# In Django shell
from django.core.cache import cache
cache.get('test')  # Test cache
```

### 3. Gunicorn Workers

Recommended formula: `(2 × CPU cores) + 1`

For t2.medium (2 vCPU):
```ini
--workers 5
```

### 4. Enable Gzip Compression

Add to Nginx config:

```nginx
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_types text/plain text/css text/xml text/javascript 
           application/json application/javascript application/xml+rss;
```

### 5. Enable HTTP/2

Already enabled in SSL config:
```nginx
listen 443 ssl http2;
```

---

## Security Checklist

- [ ] Changed all default passwords
- [ ] Generated unique SECRET_KEY and JWT_SECRET
- [ ] Configured firewall (UFW)
- [ ] Disabled root login via SSH
- [ ] Enabled HTTPS with valid certificate
- [ ] Configured Fail2Ban
- [ ] Set proper file permissions (600 for .env)
- [ ] Enabled automatic security updates
- [ ] Configured rate limiting
- [ ] Set up monitoring and alerts
- [ ] Configured log rotation
- [ ] Enabled database backups
- [ ] Tested backup restoration
- [ ] Verified CORS configuration
- [ ] Enabled security headers in Django
- [ ] Using environment variables (not hardcoded secrets)

---

## Final Verification

### Health Check

```bash
# Check all services
sudo systemctl status gunicorn celery celerybeat nginx postgresql redis

# Check application health
curl https://your-domain.com/api/v2/auth/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-16T10:30:00Z",
  "checks": {
    "database": {"status": "healthy"},
    "redis": {"status": "healthy"},
    "celery": {"status": "healthy", "workers": 1}
  }
}
```

### Load Test (Optional)

```bash
# Install Apache Bench
sudo apt install -y apache2-utils

# Test API endpoint
ab -n 1000 -c 10 https://your-domain.com/api/v2/auth/health
```

---

## Support

### Useful Commands Quick Reference

```bash
# View service status
sudo systemctl status gunicorn celery celerybeat nginx

# Restart services
sudo systemctl restart gunicorn celery celerybeat nginx

# View logs
sudo journalctl -u gunicorn -f
sudo tail -f /var/log/django/django.log

# Check disk space
df -h

# Check memory usage
free -h

# Check running processes
top
ps aux | grep python

# Database access
sudo -u postgres psql bo_journal

# Redis access
redis-cli

# Test Nginx config
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

---

**Deployment Complete!**

Your BO Journal backend is now running in production on AWS EC2 with:
- ✅ Gunicorn application server
- ✅ Nginx reverse proxy with SSL
- ✅ Celery task queue
- ✅ PostgreSQL database
- ✅ Redis caching
- ✅ Automated backups
- ✅ Security hardening
- ✅ Monitoring and logging

For API documentation, see `COMPLETE_API_DOCUMENTATION.md` series.

For issues or questions, refer to the troubleshooting section or contact the development team.
