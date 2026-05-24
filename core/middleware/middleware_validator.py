from django.http import JsonResponse


def extract_field_errors(errors):
    """Extract error messages organized by field name"""
    field_errors = {}

    if isinstance(errors, dict):
        for field_name, field_value in errors.items():
            if isinstance(field_value, list) and field_value:
                first_error = field_value[0]
                if hasattr(first_error, "detail"):
                    field_errors[field_name] = str(first_error.detail)
                elif isinstance(first_error, dict):
                    nested_msg = extract_nested_error(first_error)
                    if nested_msg:
                        field_errors[field_name] = nested_msg
                else:
                    field_errors[field_name] = str(first_error)
            elif hasattr(field_value, "detail"):
                field_errors[field_name] = str(field_value.detail)
            elif isinstance(field_value, dict):
                nested_msg = extract_nested_error(field_value)
                if nested_msg:
                    field_errors[field_name] = nested_msg
            elif isinstance(field_value, str):
                field_errors[field_name] = field_value

    return field_errors


def extract_nested_error(errors):
    """Extract error message from nested dict"""
    if isinstance(errors, dict):
        for value in errors.values():
            if isinstance(value, list) and value:
                return str(value[0])
            elif hasattr(value, "detail"):
                return str(value.detail)
            elif isinstance(value, dict):
                return extract_nested_error(value)
            elif isinstance(value, str):
                return value
    elif hasattr(errors, "detail"):
        return str(errors.detail)
    elif isinstance(errors, str):
        return errors
    return None


def extract_single_message(errors):
    """Extract a single general error message"""
    if isinstance(errors, dict) and "message" in errors:
        return str(errors["message"])

    if isinstance(errors, dict):
        for value in errors.values():
            if isinstance(value, list) and value:
                first_error = value[0]
                if hasattr(first_error, "detail"):
                    return str(first_error.detail)
                elif isinstance(first_error, dict):
                    msg = extract_nested_error(first_error)
                    if msg:
                        return msg
                else:
                    return str(first_error)
            elif hasattr(value, "detail"):
                return str(value.detail)
            elif isinstance(value, dict):
                msg = extract_nested_error(value)
                if msg:
                    return msg
            elif isinstance(value, str):
                return value

    elif isinstance(errors, list) and errors:
        first_error = errors[0]
        if hasattr(first_error, "detail"):
            return str(first_error.detail)
        elif isinstance(first_error, dict):
            msg = extract_nested_error(first_error)
            if msg:
                return msg
        else:
            return str(first_error)

    elif hasattr(errors, "detail"):
        return str(errors.detail)

    if hasattr(errors, "messages"):
        messages = errors.messages
        if messages:
            return str(messages[0])

    return None


class MiddlewareValidators:
    @staticmethod
    def handle_error(response):
        """Normalize validation errors while preserving specific endpoint messages."""
        errors = getattr(response, "data", None)

        field_errors = extract_field_errors(errors)
        message = extract_single_message(errors)

        if field_errors:
            first_error_field = list(field_errors.keys())[0]
            message = field_errors[first_error_field]
        if not message:
            message = "Los datos proporcionados son inválidos."

        response_data = {
            "success": False,
            "status": 400,
            "message": message,
            "errors": (
                {key: [value] for key, value in field_errors.items()}
                if field_errors
                else {"non_field_errors": [message]}
            ),
        }

        return JsonResponse(response_data, status=400)
