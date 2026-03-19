# Requirements Organization

This directory contains organized requirement files for different environments.

## Structure

```
requirements/
├── base.txt          # Core dependencies (all environments)
├── development.txt   # Development tools & debugging
├── production.txt    # Production server & monitoring
└── testing.txt       # Test suite dependencies
```

## Installation

### Development Environment

Install base + development dependencies:

```bash
pip install -r requirements/development.txt
```

### Production Environment

Install base + production dependencies:

```bash
pip install -r requirements/production.txt
```

### Testing Environment

Install base + testing dependencies:

```bash
pip install -r requirements/testing.txt
```

### Base Only

If you only need core functionality:

```bash
pip install -r requirements/base.txt
```

## Dependency Management

### Adding New Dependencies

1. **Core Dependencies**: Add to `base.txt` if required in all environments
2. **Development Tools**: Add to `development.txt` for dev-only packages
3. **Production Tools**: Add to `production.txt` for production-specific needs
4. **Testing Tools**: Add to `testing.txt` for test-related packages

### Updating Dependencies

To update all dependencies to latest versions:

```bash
# Development
pip install --upgrade -r requirements/development.txt

# Production
pip install --upgrade -r requirements/production.txt
```

### Freezing Current Versions

To create a lockfile with exact versions:

```bash
pip freeze > requirements-lock.txt
```

## Version Pinning Strategy

- **Major versions pinned**: Prevents breaking changes (e.g., `Django==5.2.4`)
- **Minor versions pinned**: Ensures reproducible builds
- **Patch versions allowed**: Security updates via `~=` operator (optional)

## Key Dependencies

### Base (base.txt)

- **Django 5.2.4**: Web framework
- **DRF 3.16.0**: REST API framework
- **Celery 5.5.3**: Async task queue
- **Redis 5.2.1**: Caching & message broker
- **PostgreSQL (psycopg2-binary)**: Database adapter
- **Boto3**: AWS S3 integration
- **PyJWT**: JWT authentication

### Development (development.txt)

- **Black, Flake8, Pylint**: Code quality tools
- **Pytest**: Testing framework
- **IPython, IPdb**: Interactive debugging
- **Django Debug Toolbar**: Request/query profiling
- **MyPy**: Type checking (optional)

### Production (production.txt)

- **Gunicorn**: WSGI HTTP server
- **Whitenoise**: Static file serving
- **Sentry SDK**: Error tracking
- **python-json-logger**: Structured logging
- **Hiredis**: Optimized Redis client

### Testing (testing.txt)

- **Pytest + plugins**: Test execution & coverage
- **Factory Boy**: Test data generation
- **Freezegun**: Time mocking
- **Responses**: HTTP mocking

## Migration from Monolithic requirements.txt

If you have an existing `requirements.txt`:

1. **Backup**: `cp requirements.txt requirements.txt.backup`
2. **Categorize**: Move dependencies to appropriate files
3. **Test**: Install and run tests in each environment
4. **Update CI/CD**: Change pip install commands
5. **Document**: Update README with new installation instructions

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements/testing.txt
```

### Docker Example

```dockerfile
# Development
FROM python:3.11-slim
COPY requirements/development.txt .
RUN pip install -r development.txt

# Production
FROM python:3.11-slim
COPY requirements/production.txt .
RUN pip install -r production.txt
```

## Troubleshooting

### Dependency Conflicts

If you encounter conflicts:

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements/<env>.txt --force-reinstall
```

### Missing System Libraries

Some packages require system libraries:

```bash
# PostgreSQL
sudo apt-get install libpq-dev

# Redis (hiredis)
sudo apt-get install build-essential

# Pillow (if using images)
sudo apt-get install libjpeg-dev zlib1g-dev
```

### Virtual Environment

Always use a virtual environment:

```bash
python -m venv env
source env/bin/activate  # Linux/Mac
# or
env\Scripts\activate  # Windows

pip install -r requirements/development.txt
```

## Best Practices

1. **Pin exact versions** for reproducibility
2. **Separate concerns** by environment
3. **Use `-r` includes** to avoid duplication
4. **Regular updates** for security patches
5. **Test upgrades** in development first
6. **Document special requirements** (system libraries, etc.)
7. **Keep requirements minimal** - only install what's needed

## Security

- Run `pip audit` regularly to check for vulnerabilities
- Update dependencies promptly for security patches
- Use `pip-audit` or `safety` tools in CI/CD

```bash
pip install pip-audit
pip-audit -r requirements/production.txt
```
