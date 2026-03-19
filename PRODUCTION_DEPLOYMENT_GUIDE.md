# BO Journal - Production Deployment Guide

**Target Platform**: AWS EC2 Ubuntu 22.04 LTS  
**Last Updated**: November 16, 2025

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Server Setup](#initial-server-setup)
3. [Install System Dependencies](#install-system-dependencies)
4. [PostgreSQL Setup](#postgresql-setup)
5. [Redis Setup](#redis-setup)
6. [Application Deployment](#application-deployment)
7. [Gunicorn Setup](#gunicorn-setup)
8. [Nginx Setup](#nginx-setup)
9. [SSL/TLS Configuration](#ssltls-configuration)
10. [Celery Setup](#celery-setup)
11. [Environment Configuration](#environment-configuration)
12. [Security Hardening](#security-hardening)
13. [Monitoring & Logging](#monitoring--logging)
14. [Backup Strategy](#backup-strategy)
15. [Maintenance](#maintenance)
16. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### AWS EC2 Instance
- **Instance Type**: t2.medium or better (2 vCPU, 4GB RAM minimum)
- **OS**: Ubuntu 22.04 LTS
- **Storage**: 30GB minimum SSD
- **Security Group**: Ports 80, 443, 22 open

### Domain Setup
- Domain name purchased and configured
- DNS A record pointing to EC2 instance IP

### External Services
- PostgreSQL database (RDS recommended) OR local installation
- Redis instance (ElastiCache recommended) OR local installation
- AWS S3 bucket for file storage
- Razorpay account for payments
- SMTP email service (Gmail, SendGrid, or AWS SES)

### Local Requirements
- SSH key pair for EC2 access
- Git repository access

---

## Initial Server Setup

### 1. Connect to Server

```bash
# Connect via SSH
ssh -i your-key.pem ubuntu@your-server-ip

# Update system packages
sudo apt update && sudo apt upgrade -y
```

### 2. Create Application User

```bash
# Create dedicated user for application
sudo adduser --system --group --home /home/bojournal bojournal

# Add to sudo group (optional, for convenience)
sudo usermod -aG sudo bojournal
```

### 3. Configure Firewall

```bash
# Install UFW if not present
sudo apt install ufw -y

# Allow SSH (IMPORTANT: Do this first!)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### 4. Configure SSH Security

```bash
# Edit SSH config
sudo nano /etc/ssh/sshd_config

# Make these changes:
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes

# Restart SSH
sudo systemctl restart sshd
```

---

## Install System Dependencies

### 1. System Packages

```bash
# Python and build tools
sudo apt install -y python3.11 python3.11-venv python3-pip python3.11-dev

# Build essentials
sudo apt install -y build-essential libssl-dev libffi-dev

# PostgreSQL client libraries
sudo apt install -y libpq-dev

# Other utilities
sudo apt install -y git curl wget nginx supervisor
```

### 2. Set Python 3.11 as Default

```bash
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
python3 --version  # Should show 3.11.x
```

---

## PostgreSQL Setup

### Option A: AWS RDS (Recommended for Production)

1. Create RDS PostgreSQL instance via AWS Console
2. Configure security group to allow connections from EC2
3. Note down endpoint, database name, username, password
4. Skip to [Application Deployment](#application-deployment)

### Option B: Local Installation

```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Start and enable service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE bo_journal;
CREATE USER bojournal_user WITH PASSWORD 'your_secure_password';
ALTER ROLE bojournal_user SET client_encoding TO 'utf8';
ALTER ROLE bojournal_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE bojournal_user SET timezone TO 'Asia/Kolkata';
GRANT ALL PRIVILEGES ON DATABASE bo_journal TO bojournal_user;
\q
EOF

# Configure PostgreSQL for remote connections (if needed)
sudo nano /etc/postgresql/14/main/postgresql.conf
# Set: listen_addresses = 'localhost'

sudo nano /etc/postgresql/14/main/pg_hba.conf
# Add: host    bo_journal    bojournal_user    127.0.0.1/32    md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

---

## Redis Setup

### Option A: AWS ElastiCache (Recommended for Production)

1. Create ElastiCache Redis cluster via AWS Console
2. Configure security group to allow connections from EC2
3. Note down endpoint URL
4. Skip to [Application Deployment](#application-deployment)

### Option B: Local Installation

```bash
# Install Redis
sudo apt install -y redis-server

# Configure Redis
sudo nano /etc/redis/redis.conf

# Make these changes:
supervised systemd
bind 127.0.0.1
maxmemory 256mb
maxmemory-policy allkeys-lru

# Start and enable Redis
sudo systemctl start redis
sudo systemctl enable redis

# Test Redis
redis-cli ping  # Should return PONG
```

---

## Application Deployment

### 1. Clone Repository

```bash
# Switch to application user
sudo su - bojournal

# Clone repository
cd /home/bojournal
git clone https://github.com/your-org/bo-journal-backend.git
cd bo-journal-backend
```

### 2. Create Virtual Environment

```bash
# Create venv
python3 -m venv env

# Activate venv
source env/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

### 3. Install Python Dependencies

```bash
# Navigate to django project
cd backend/django_backend

# Install production dependencies
pip install -r ../../requirements/production.txt

# Install Gunicorn
pip install gunicorn
```

### 4. Configure Environment Variables

```bash
# Create .env file
nano .env

# Add configuration (see Environment Configuration section below)
```

### 5. Run Migrations

```bash
# Set environment
export DJANGO_ENVIRONMENT=production

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 6. Collect Static Files

```bash
# Collect static files
python manage.py collectstatic --noinput
```

### 7. Test Application

```bash
# Test server (development mode)
python manage.py runserver 0.0.0.0:8000

# Visit http://your-ip:8000/admin
# If working, proceed to Gunicorn setup
```

---

## Gunicorn Setup

### 1. Test Gunicorn

```bash
# From django_backend directory
gunicorn --bind 0.0.0.0:8000 django_backend.wsgi:application
```

### 2. Create Gunicorn Socket

```bash
# Exit from bojournal user
exit

# Create socket file
sudo nano /etc/systemd/system/gunicorn.socket
```

**gunicorn.socket:**
```ini
[Unit]
Description=gunicorn socket

[Socket]
ListenStream=/run/gunicorn.sock

[Install]
WantedBy=sockets.target
```

### 3. Create Gunicorn Service

```bash
sudo nano /etc/systemd/system/gunicorn.service
```

**gunicorn.service:**
```ini
[Unit]
Description=gunicorn daemon for BO Journal
Requires=gunicorn.socket
After=network.target

[Service]
Type=notify
User=bojournal
Group=bojournal
WorkingDirectory=/home/bojournal/bo-journal-backend/backend/django_backend
Environment="PATH=/home/bojournal/bo-journal-backend/backend/env/bin"
Environment="DJANGO_ENVIRONMENT=production"
ExecStart=/home/bojournal/bo-journal-backend/backend/env/bin/gunicorn \
          --access-logfile /var/log/gunicorn/access.log \
          --error-logfile /var/log/gunicorn/error.log \
          --workers 3 \
          --bind unix:/run/gunicorn.sock \
          --timeout 60 \
          --graceful-timeout 30 \
          django_backend.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### 4. Create Log Directory

```bash
sudo mkdir -p /var/log/gunicorn
sudo chown bojournal:bojournal /var/log/gunicorn
```

### 5. Start Gunicorn

```bash
# Start and enable socket
sudo systemctl start gunicorn.socket
sudo systemctl enable gunicorn.socket

# Check socket status
sudo systemctl status gunicorn.socket

# Test socket activation (this starts the service)
curl --unix-socket /run/gunicorn.sock localhost

# Check service status
sudo systemctl status gunicorn

# Enable service
sudo systemctl enable gunicorn
```

### 6. Reload After Code Changes

```bash
# After git pull or code changes
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
```

---

## Nginx Setup

### 1. Install Nginx

```bash
sudo apt install -y nginx
```

### 2. Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/bojournal
```

**bojournal (HTTP only, for now):**
```nginx
upstream gunicorn {
    server unix:/run/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    client_max_body_size 20M;

    # Logging
    access_log /var/log/nginx/bojournal_access.log;
    error_log /var/log/nginx/bojournal_error.log;

    # Static files
    location /static/ {
        alias /home/bojournal/bo-journal-backend/backend/django_backend/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files (if any served directly)
    location /media/ {
        alias /home/bojournal/bo-journal-backend/backend/django_backend/media/;
    }

    # API endpoints
    location / {
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_buffering off;
        
        proxy_pass http://gunicorn;
    }
}
```

### 3. Enable Site

```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/bojournal /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 4. Test HTTP Access

Visit `http://your-domain.com/admin` - should see Django admin login.

---

## SSL/TLS Configuration

### 1. Install Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 2. Obtain SSL Certificate

```bash
# Get certificate (automatically configures Nginx)
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Follow prompts:
# - Enter email
# - Agree to terms
# - Redirect HTTP to HTTPS: Yes
```

### 3. Update Nginx Configuration

Certbot auto-updates, but verify:

```bash
sudo nano /etc/nginx/sites-available/bojournal
```

Should now include:

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # ... rest of configuration
}

server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$host$request_uri;
}
```

### 4. Test Auto-Renewal

```bash
# Dry run
sudo certbot renew --dry-run

# Certbot automatically sets up cron job for renewal
```

### 5. Verify HTTPS

Visit `https://your-domain.com` - should see secure connection.

---

## Celery Setup

### 1. Create Celery Worker Service

```bash
sudo nano /etc/systemd/system/celery.service
```

**celery.service:**
```ini
[Unit]
Description=Celery Worker for BO Journal
After=network.target redis.service postgresql.service

[Service]
Type=forking
User=bojournal
Group=bojournal
WorkingDirectory=/home/bojournal/bo-journal-backend/backend/django_backend
Environment="PATH=/home/bojournal/bo-journal-backend/backend/env/bin"
Environment="DJANGO_ENVIRONMENT=production"
ExecStart=/home/bojournal/bo-journal-backend/backend/env/bin/celery -A django_backend worker \
          --loglevel=info \
          --logfile=/var/log/celery/worker.log \
          --pidfile=/var/run/celery/worker.pid \
          --detach
ExecStop=/bin/kill -s TERM $MAINPID
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

### 2. Create Celery Beat Service

```bash
sudo nano /etc/systemd/system/celerybeat.service
```

**celerybeat.service:**
```ini
[Unit]
Description=Celery Beat Scheduler for BO Journal
After=network.target redis.service

[Service]
Type=simple
User=bojournal
Group=bojournal
WorkingDirectory=/home/bojournal/bo-journal-backend/backend/django_backend
Environment="PATH=/home/bojournal/bo-journal-backend/backend/env/bin"
Environment="DJANGO_ENVIRONMENT=production"
ExecStart=/home/bojournal/bo-journal-backend/backend/env/bin/celery -A django_backend beat \
          --loglevel=info \
          --logfile=/var/log/celery/beat.log \
          --pidfile=/var/run/celery/beat.pid \
          --schedule=/var/run/celery/celerybeat-schedule
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

### 3. Create Celery Directories

```bash
sudo mkdir -p /var/log/celery /var/run/celery
sudo chown bojournal:bojournal /var/log/celery /var/run/celery
```

### 4. Start Celery Services

```bash
# Start and enable worker
sudo systemctl start celery
sudo systemctl enable celery
sudo systemctl status celery

# Start and enable beat
sudo systemctl start celerybeat
sudo systemctl enable celerybeat
sudo systemctl status celerybeat
```

### 5. Monitor Celery

```bash
# View worker logs
sudo tail -f /var/log/celery/worker.log

# View beat logs
sudo tail -f /var/log/celery/beat.log

# Restart after code changes
sudo systemctl restart celery celerybeat
```

---

*[Continued in PRODUCTION_DEPLOYMENT_GUIDE_PART2.md...]*
