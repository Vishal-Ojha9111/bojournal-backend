import logging
import traceback
from django.utils.encoding import force_str
from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError as DRFValidationError, NotFound, PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError

logger = logging.getLogger(__name__)

def _extract_message_from_payload(payload):
    """
    Walk the payload to extract a concise message string.
    Handles dicts, lists, strings, nested structures.
    Returns (message_str, original_payload) where original_payload can be used as 'errors'.
    """
    if payload is None:
        return None, None

    # If it's already a string
    if isinstance(payload, str):
        return payload, None

    # If it's a list, pick first non-empty element
    if isinstance(payload, (list, tuple)):
        for item in payload:
            msg, _ = _extract_message_from_payload(item)
            if msg:
                return msg, payload
        return None, payload

    # If dict-like, prefer 'detail' key, else first value
    if isinstance(payload, dict):
        # common shape: {'field': ['err1', 'err2'], 'non_field_errors': ['x']}
        candidates = []
        if 'detail' in payload:
            candidates.append(payload['detail'])
        # gather first-level values
        for v in payload.values():
            candidates.append(v)
        for candidate in candidates:
            msg, _ = _extract_message_from_payload(candidate)
            if msg:
                return msg, payload
        return None, payload

    # Fallback: force to string (coerce booleans/numbers)
    try:
        return force_str(payload), None
    except Exception:
        return None, payload


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler that returns a consistent payload:
    {
      "status": False,
      "message": "<user friendly message>",
      "errors": <original response.data for structured errors, optional>
    }

    - For validation errors, returns the first user-friendly validation message and 'errors' with full details.
    - For 5xx (server) errors, returns a generic message to clients and logs details for server-side debugging.
    """
    # Let DRF build the default response first
    response = exception_handler(exc, context)
    if response is None:
        # Not an exception we want to customize (or it's an unhandled server error)
        # Let Django/DRF handle it further (or you could generate a generic 500)
        return response

    # Use the final response.payload as source of truth when possible
    payload = getattr(response, 'data', None)
    # If response.data is None, fall back to exc.detail
    if payload is None:
        payload = getattr(exc, 'detail', None)

    # Extract a top-level friendly message and keep the structured payload as errors
    message, errors = _extract_message_from_payload(payload)

    # Build sanitized response
    safe_payload = {
        "status": False,
        "message": message or "An error occurred"
    }

    # Keep structured errors for clients that need them (but don't expose internals for 5xx)
    status_code = getattr(response, 'status_code', None) or 500
    if status_code >= 500:
        # Log full details for debugging
        try:
            logger.error("Internal server error: %s\nContext: %s\nTraceback: %s", 
                         exc, 
                         context,
                         traceback.format_exc())
        except Exception:
            logger.exception("Failed logging internal exception")

        # Generic message for clients
        safe_payload["message"] = "Internal server error"
        # Optionally include a correlation id if you have one for tracing
    else:
        # For client errors (4xx), preserve structured details under "errors"
        if errors is not None:
            safe_payload["errors"] = errors
        else:
            # For cases where payload is simple, include it only if it's not redundant
            if isinstance(payload, (dict, list)) and payload:
                safe_payload["errors"] = payload

    response.data = safe_payload
    return response
