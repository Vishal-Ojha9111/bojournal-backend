"""
Date validation utilities for API query parameters.

This module provides reusable date validation functions to ensure
date parameters are validated BEFORE any database queries are executed.
"""

from django.utils.dateparse import parse_date
from django.utils import timezone
from rest_framework.response import Response
from typing import Optional, Tuple, Dict, Any
import datetime


class DateValidationError(Exception):
    """Custom exception for date validation errors."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def validate_date_format(date_str: str, param_name: str = "date") -> Optional[datetime.date]:
    """
    Validate and parse a date string.
    
    Args:
        date_str: Date string to validate (expected format: YYYY-MM-DD)
        param_name: Name of the parameter (for error messages)
    
    Returns:
        Parsed date object if valid, None otherwise
    
    Raises:
        DateValidationError: If date format is invalid
    """
    if not date_str:
        return None
    
    parsed_date = parse_date(date_str)
    if not parsed_date:
        raise DateValidationError(
            f"Invalid date format for '{param_name}'. Use YYYY-MM-DD format (e.g., 2025-11-18).",
            status_code=400
        )
    
    return parsed_date


def validate_not_future_date(date: datetime.date, param_name: str = "date") -> None:
    """
    Ensure date is not in the future.
    
    Args:
        date: Date to validate
        param_name: Name of the parameter (for error messages)
    
    Raises:
        DateValidationError: If date is in the future
    """
    today = timezone.localdate()
    if date > today:
        raise DateValidationError(
            f"'{param_name}' cannot be in the future. "
            f"Requested '{date}' is beyond today ({today}).",
            status_code=400
        )


def validate_not_before_date(date: datetime.date, min_date: datetime.date, 
                             param_name: str = "date", 
                             context: str = "allowed date") -> None:
    """
    Ensure date is not before a minimum allowed date.
    
    Args:
        date: Date to validate
        min_date: Minimum allowed date
        param_name: Name of the parameter (for error messages)
        context: Context for the minimum date (e.g., "first opening balance date")
    
    Raises:
        DateValidationError: If date is before minimum date
    """
    if date < min_date:
        raise DateValidationError(
            f"'{param_name}' ({date}) is before {context} ({min_date}).",
            status_code=400
        )


def validate_date_range_logic(start_date: Optional[datetime.date], 
                              end_date: Optional[datetime.date]) -> None:
    """
    Ensure date range has valid logic (start <= end).
    
    Args:
        start_date: Start date of range
        end_date: End date of range
    
    Raises:
        DateValidationError: If start_date is after end_date
    """
    if start_date and end_date and start_date > end_date:
        raise DateValidationError(
            f"'start_date' ({start_date}) cannot be after 'end_date' ({end_date}).",
            status_code=400
        )


def validate_date_range_size(start_date: datetime.date, 
                             end_date: datetime.date, 
                             max_days: int = 365) -> None:
    """
    Ensure date range is not excessively large (performance safeguard).
    
    Args:
        start_date: Start date of range
        end_date: End date of range
        max_days: Maximum allowed range in days
    
    Raises:
        DateValidationError: If date range exceeds max_days
    """
    date_diff = (end_date - start_date).days
    if date_diff > max_days:
        raise DateValidationError(
            f"Date range too large ({date_diff} days). "
            f"Maximum allowed range is {max_days} days. "
            f"Please use smaller date ranges.",
            status_code=400
        )


def validate_no_conflicting_params(single_date: Optional[str], 
                                   start_date: Optional[str], 
                                   end_date: Optional[str]) -> None:
    """
    Ensure date parameters are not conflicting.
    
    Args:
        single_date: Single date parameter value
        start_date: Start date parameter value
        end_date: End date parameter value
    
    Raises:
        DateValidationError: If conflicting parameters are provided
    """
    if single_date and (start_date or end_date):
        raise DateValidationError(
            "Cannot use 'date' parameter together with 'start_date' or 'end_date'. "
            "Use either single date or date range.",
            status_code=400
        )


def validate_query_dates(
    single_date_str: Optional[str] = None,
    start_date_str: Optional[str] = None,
    end_date_str: Optional[str] = None,
    min_allowed_date: Optional[datetime.date] = None,
    max_days_range: int = 365,
    allow_future: bool = False,
    min_date_context: str = "minimum allowed date"
) -> Dict[str, Optional[datetime.date]]:
    """
    Comprehensive validation for date query parameters.
    
    This is the main function that orchestrates all date validations.
    It validates format, business logic, and returns parsed dates.
    
    Args:
        single_date_str: Single date parameter (format: YYYY-MM-DD)
        start_date_str: Start date of range (format: YYYY-MM-DD)
        end_date_str: End date of range (format: YYYY-MM-DD)
        min_allowed_date: Minimum allowed date (e.g., user's first opening balance date)
        max_days_range: Maximum allowed date range in days (default: 365)
        allow_future: Whether to allow future dates (default: False)
        min_date_context: Context description for min_allowed_date (for error messages)
    
    Returns:
        Dictionary with parsed dates:
        {
            'single_date': parsed_date or None,
            'start_date': parsed_start or None,
            'end_date': parsed_end or None
        }
    
    Raises:
        DateValidationError: If any validation fails
    
    Example:
        ```python
        try:
            dates = validate_query_dates(
                single_date_str=request.query_params.get('date'),
                start_date_str=request.query_params.get('start_date'),
                end_date_str=request.query_params.get('end_date'),
                min_allowed_date=user.first_opening_balance_date,
                min_date_context="first opening balance date"
            )
            single_date = dates['single_date']
            start_date = dates['start_date']
            end_date = dates['end_date']
        except DateValidationError as e:
            return Response({
                "status": False,
                "message": e.message
            }, status=e.status_code)
        ```
    """
    
    # Check for conflicting parameters
    validate_no_conflicting_params(single_date_str, start_date_str, end_date_str)
    
    parsed_single = None
    parsed_start = None
    parsed_end = None
    
    # Validate single date parameter
    if single_date_str:
        parsed_single = validate_date_format(single_date_str, "date")
        
        # Check if date is in the future
        if not allow_future:
            validate_not_future_date(parsed_single, "date")
        
        # Check if date is before minimum allowed date
        if min_allowed_date:
            validate_not_before_date(
                parsed_single, 
                min_allowed_date, 
                "date", 
                min_date_context
            )
    
    # Validate date range parameters
    elif start_date_str or end_date_str:
        # Parse and validate start_date
        if start_date_str:
            parsed_start = validate_date_format(start_date_str, "start_date")
            
            if not allow_future:
                validate_not_future_date(parsed_start, "start_date")
            
            if min_allowed_date:
                validate_not_before_date(
                    parsed_start, 
                    min_allowed_date, 
                    "start_date", 
                    min_date_context
                )
        
        # Parse and validate end_date
        if end_date_str:
            parsed_end = validate_date_format(end_date_str, "end_date")
            
            if not allow_future:
                validate_not_future_date(parsed_end, "end_date")
            
            if min_allowed_date:
                validate_not_before_date(
                    parsed_end, 
                    min_allowed_date, 
                    "end_date", 
                    min_date_context
                )
        
        # Validate date range logic
        validate_date_range_logic(parsed_start, parsed_end)
        
        # Validate date range size (only if both dates provided)
        if parsed_start and parsed_end:
            validate_date_range_size(parsed_start, parsed_end, max_days_range)
    
    return {
        'single_date': parsed_single,
        'start_date': parsed_start,
        'end_date': parsed_end
    }


def create_date_error_response(error: DateValidationError) -> Response:
    """
    Create a standardized error response for date validation errors.
    
    Args:
        error: DateValidationError exception
    
    Returns:
        Response object with error details
    """
    return Response({
        "status": False,
        "message": error.message
    }, status=error.status_code)


def validate_single_date_param(
    date_str: Optional[str],
    min_allowed_date: Optional[datetime.date] = None,
    allow_future: bool = False,
    param_name: str = "date",
    min_date_context: str = "minimum allowed date"
) -> Optional[datetime.date]:
    """
    Quick validation for a single date parameter (simplified version).
    
    Args:
        date_str: Date string to validate
        min_allowed_date: Minimum allowed date
        allow_future: Whether to allow future dates
        param_name: Name of the parameter (for error messages)
        min_date_context: Context for minimum date
    
    Returns:
        Parsed date or None if date_str is empty
    
    Raises:
        DateValidationError: If validation fails
    
    Example:
        ```python
        try:
            date = validate_single_date_param(
                request.data.get('date'),
                min_allowed_date=user.first_opening_balance_date,
                min_date_context="first opening balance date"
            )
        except DateValidationError as e:
            return Response({"status": False, "message": e.message}, status=e.status_code)
        ```
    """
    if not date_str:
        return None
    
    parsed_date = validate_date_format(date_str, param_name)
    
    if not allow_future:
        validate_not_future_date(parsed_date, param_name)
    
    if min_allowed_date:
        validate_not_before_date(parsed_date, min_allowed_date, param_name, min_date_context)
    
    return parsed_date
