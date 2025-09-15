from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError

def custom_exception_handler(exc, context):
    # Get the default DRF response
    response = exception_handler(exc, context)

    if response is not None:
        # Copy the original details to avoid mutation issues
        details_copy = getattr(exc, 'detail', None)

        # Start with a clean data dict
        response.data = {}
        response.data["status"] = False

        # Handle DRF & Django ValidationError
        if isinstance(exc, (ValidationError, DjangoValidationError)):
            message = "Validation error"

            if isinstance(details_copy, dict):
                first_val = next(iter(details_copy.values()), None)
                if isinstance(first_val, list) and first_val:
                    message = str(first_val[0])
                else:
                    message = str(first_val)
            elif isinstance(details_copy, list) and details_copy:
                message = str(details_copy[0])
            elif isinstance(details_copy, str):
                message = details_copy
            elif isinstance(details_copy, bool):
                message = str(details_copy)
            else:
                message = str(details_copy)

            response.data["message"] = message

        # Handle NotFound
        elif isinstance(exc, NotFound):
            response.data["message"] = str(details_copy)

        # Handle PermissionDenied
        elif isinstance(exc, PermissionDenied):
            response.data["message"] = str(details_copy)

        # Fallback
        else:
            response.data["message"] = str(details_copy) if details_copy else str(exc)

    return response
