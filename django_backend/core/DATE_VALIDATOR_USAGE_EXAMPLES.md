# Date Validation Utility - Usage Examples

## Overview
The `core/date_validators.py` module provides reusable date validation functions that can be used across all APIs (journal, transactions, holidays, etc.) to validate date query parameters **before** any database queries.

---

## Import Statement

```python
from core.date_validators import (
    validate_query_dates, 
    validate_single_date_param,
    DateValidationError, 
    create_date_error_response
)
```

---

## Example 1: Journal API (List View)

**Use Case**: Validate date range queries with opening balance date check

```python
def list(self, request):
    user = request.user
    
    # Get query parameters
    single_date_str = request.query_params.get("date", "")
    start_date_str = request.query_params.get("start_date", "")
    end_date_str = request.query_params.get("end_date", "")
    
    # Validate dates using utility function
    try:
        dates = validate_query_dates(
            single_date_str=single_date_str or None,
            start_date_str=start_date_str or None,
            end_date_str=end_date_str or None,
            min_allowed_date=user.first_opening_balance_date,
            max_days_range=365,  # Maximum 1 year range
            allow_future=False,  # No future dates
            min_date_context="first opening balance date"
        )
        parsed_single = dates['single_date']
        parsed_start = dates['start_date']
        parsed_end = dates['end_date']
    except DateValidationError as e:
        return create_date_error_response(e)
    
    # Use validated dates for database queries
    journals = Journal.objects.filter(user=user)
    if parsed_single:
        journals = journals.filter(date=parsed_single)
    elif parsed_start and parsed_end:
        journals = journals.filter(date__range=[parsed_start, parsed_end])
    # ... rest of logic
```

---

## Example 2: Transactions API (List View)

**Use Case**: Validate date range queries for transaction filtering

```python
def list(self, request):
    user = request.user
    
    # Get query parameters
    single_date_str = request.query_params.get("date")
    start_date_str = request.query_params.get("start_date")
    end_date_str = request.query_params.get("end_date")
    
    # Validate dates
    try:
        dates = validate_query_dates(
            single_date_str=single_date_str,
            start_date_str=start_date_str,
            end_date_str=end_date_str,
            min_allowed_date=user.first_opening_balance_date,
            max_days_range=365,
            allow_future=False,
            min_date_context="first opening balance date"
        )
    except DateValidationError as e:
        return create_date_error_response(e)
    
    # Apply validated date filters
    transactions = Transaction.objects.filter(user=user)
    if dates['single_date']:
        transactions = transactions.filter(date=dates['single_date'])
    elif dates['start_date'] and dates['end_date']:
        transactions = transactions.filter(
            date__range=[dates['start_date'], dates['end_date']]
        )
    elif dates['start_date']:
        transactions = transactions.filter(date__gte=dates['start_date'])
    elif dates['end_date']:
        transactions = transactions.filter(date__lte=dates['end_date'])
    
    # ... rest of logic
```

---

## Example 3: Transaction Creation

**Use Case**: Validate single date when creating a transaction

```python
def create(self, request):
    user = request.user
    date_str = request.data.get('date')
    
    if not date_str:
        return Response({
            "status": False, 
            "message": "'date' is required."
        }, status=400)
    
    # Validate single date
    try:
        date = validate_single_date_param(
            date_str,
            min_allowed_date=user.first_opening_balance_date,
            allow_future=False,  # Transactions can't be in future
            param_name="date",
            min_date_context="first opening balance date"
        )
    except DateValidationError as e:
        return create_date_error_response(e)
    
    # Create transaction with validated date
    transaction = Transaction.objects.create(
        user=user,
        date=date,
        amount=request.data.get('amount'),
        # ... other fields
    )
    
    return Response({
        "status": True,
        "message": "Transaction created successfully."
    })
```

---

## Example 4: Holiday API

**Use Case**: Allow future dates for holiday scheduling

```python
def create(self, request):
    user = request.user
    date_str = request.data.get('date')
    
    # Validate date (allow future dates for holiday planning)
    try:
        date = validate_single_date_param(
            date_str,
            min_allowed_date=user.first_opening_balance_date,
            allow_future=True,  # Allow future holidays
            param_name="date",
            min_date_context="first opening balance date"
        )
    except DateValidationError as e:
        return create_date_error_response(e)
    
    # Create holiday
    holiday = Holiday.objects.create(
        user=user,
        date=date,
        reason=request.data.get('reason')
    )
    
    return Response({
        "status": True,
        "message": "Holiday created successfully."
    })
```

---

## Example 5: Custom Date Range (Different Max Days)

**Use Case**: API with different performance requirements

```python
def get_summary(self, request):
    """Get summary report - allow longer date ranges"""
    
    try:
        dates = validate_query_dates(
            start_date_str=request.query_params.get('start_date'),
            end_date_str=request.query_params.get('end_date'),
            max_days_range=730,  # Allow 2 years for summary reports
            allow_future=False
        )
    except DateValidationError as e:
        return create_date_error_response(e)
    
    # Generate summary with validated dates
    # ...
```

---

## Example 6: No Minimum Date Restriction

**Use Case**: Admin API or initial setup where no minimum date applies

```python
def admin_query(self, request):
    """Admin endpoint - no date restrictions"""
    
    try:
        dates = validate_query_dates(
            start_date_str=request.query_params.get('start_date'),
            end_date_str=request.query_params.get('end_date'),
            min_allowed_date=None,  # No minimum date restriction
            allow_future=True,  # Allow future dates
            max_days_range=1825  # 5 years
        )
    except DateValidationError as e:
        return create_date_error_response(e)
    
    # Process with validated dates
    # ...
```

---

## Validation Features

### ✅ Automatic Validations

When you call `validate_query_dates()` or `validate_single_date_param()`, these checks are performed automatically:

1. **Date Format**: Validates YYYY-MM-DD format
2. **Conflicting Parameters**: Prevents using `date` with `start_date`/`end_date`
3. **Future Dates**: Checks if dates are in the future (configurable)
4. **Minimum Date**: Validates against minimum allowed date (e.g., opening balance)
5. **Range Logic**: Ensures start_date ≤ end_date
6. **Range Size**: Limits maximum date range (performance safeguard)

---

## Error Handling

### Standard Pattern

```python
try:
    dates = validate_query_dates(...)
except DateValidationError as e:
    return create_date_error_response(e)
```

### Custom Error Handling

```python
try:
    dates = validate_query_dates(...)
except DateValidationError as e:
    # Log error
    logger.warning(f"Date validation failed: {e.message}")
    
    # Return custom response
    return Response({
        "status": False,
        "message": e.message,
        "code": "INVALID_DATE"
    }, status=e.status_code)
```

---

## Configuration Options

### validate_query_dates() Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `single_date_str` | str \| None | None | Single date query parameter |
| `start_date_str` | str \| None | None | Range start date |
| `end_date_str` | str \| None | None | Range end date |
| `min_allowed_date` | date \| None | None | Minimum allowed date |
| `max_days_range` | int | 365 | Maximum date range in days |
| `allow_future` | bool | False | Allow future dates |
| `min_date_context` | str | "minimum allowed date" | Error message context |

### validate_single_date_param() Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `date_str` | str \| None | None | Date string to validate |
| `min_allowed_date` | date \| None | None | Minimum allowed date |
| `allow_future` | bool | False | Allow future dates |
| `param_name` | str | "date" | Parameter name for errors |
| `min_date_context` | str | "minimum allowed date" | Error message context |

---

## Return Values

### validate_query_dates() Returns

```python
{
    'single_date': datetime.date | None,  # Parsed single date
    'start_date': datetime.date | None,   # Parsed start date
    'end_date': datetime.date | None      # Parsed end date
}
```

### validate_single_date_param() Returns

```python
datetime.date | None  # Parsed date or None if empty
```

---

## Common Patterns

### Pattern 1: Query Parameters (GET)

```python
# In list/retrieve endpoints
dates = validate_query_dates(
    single_date_str=request.query_params.get('date'),
    start_date_str=request.query_params.get('start_date'),
    end_date_str=request.query_params.get('end_date'),
    min_allowed_date=user.first_opening_balance_date,
    allow_future=False
)
```

### Pattern 2: Request Body (POST/PUT)

```python
# In create/update endpoints
date = validate_single_date_param(
    request.data.get('date'),
    min_allowed_date=user.first_opening_balance_date,
    allow_future=False
)
```

### Pattern 3: With Required Check

```python
date_str = request.data.get('date')
if not date_str:
    return Response({"status": False, "message": "'date' is required."}, status=400)

date = validate_single_date_param(date_str, ...)
```

---

## Benefits

✅ **DRY (Don't Repeat Yourself)**: Write validation once, use everywhere
✅ **Consistent Error Messages**: Standardized error format across all APIs
✅ **Performance**: Validates before database queries
✅ **Maintainable**: Change validation logic in one place
✅ **Testable**: Easy to unit test validation logic
✅ **Type Safe**: Returns typed date objects
✅ **Configurable**: Flexible parameters for different use cases

---

## Testing

### Unit Test Example

```python
from core.date_validators import validate_single_date_param, DateValidationError
from django.utils import timezone
import pytest

def test_valid_date():
    date = validate_single_date_param("2025-11-18")
    assert date.year == 2025
    assert date.month == 11
    assert date.day == 18

def test_invalid_format():
    with pytest.raises(DateValidationError) as e:
        validate_single_date_param("18-11-2025")
    assert "Invalid date format" in str(e.value)

def test_future_date_not_allowed():
    future_date = (timezone.localdate() + timedelta(days=1)).isoformat()
    with pytest.raises(DateValidationError) as e:
        validate_single_date_param(future_date, allow_future=False)
    assert "cannot be in the future" in str(e.value)

def test_before_minimum_date():
    with pytest.raises(DateValidationError) as e:
        validate_single_date_param(
            "2025-01-01",
            min_allowed_date=date(2025, 3, 1),
            min_date_context="opening date"
        )
    assert "before opening date" in str(e.value)
```

---

## Migration Guide

### Before (Without Utility)

```python
# Lots of repetitive code
date_str = request.query_params.get('date')
if date_str:
    date = parse_date(date_str)
    if not date:
        return Response({"error": "Invalid date"}, status=400)
    if date > timezone.localdate():
        return Response({"error": "Future date"}, status=400)
    if date < user.first_opening_balance_date:
        return Response({"error": "Before opening"}, status=400)
```

### After (With Utility)

```python
# Clean and simple
try:
    date = validate_single_date_param(
        request.query_params.get('date'),
        min_allowed_date=user.first_opening_balance_date,
        allow_future=False
    )
except DateValidationError as e:
    return create_date_error_response(e)
```

---

## Summary

The date validation utility provides:
- ✅ Comprehensive date validation in one function call
- ✅ Consistent error messages across all APIs
- ✅ Performance optimization (validates before DB queries)
- ✅ Reusable across journal, transactions, holidays, and other APIs
- ✅ Configurable for different use cases
- ✅ Easy to test and maintain

Use `validate_query_dates()` for list endpoints with query parameters.
Use `validate_single_date_param()` for create/update endpoints with single dates.
