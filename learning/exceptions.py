from rest_framework.views import exception_handler
from rest_framework.response import Response
from django.http import Http404


class NotFoundException(Exception):
    pass


class ConflictException(Exception):
    pass


class ValidationException(Exception):
    pass


def rfc7807_exception_handler(exc, context):
    request = context.get("request")
    path = request.path if request else ""

    if isinstance(exc, (NotFoundException, Http404)):
        status_code = 404
        title = "Resource not found"
        detail = str(exc)
    elif isinstance(exc, ConflictException):
        status_code = 409
        title = "Resource conflict"
        detail = str(exc)
    elif isinstance(exc, ValidationException):
        status_code = 422
        title = "Business rule violation"
        detail = str(exc)
    else:
        response = exception_handler(exc, context)
        if response is not None:
            status_code = response.status_code
            title = "Validation error" if status_code == 400 else "Error"
            detail = response.data
        else:
            status_code = 500
            title = "An unexpected error occurred"
            detail = "The server could not complete the request."

    return Response(
        {
            "title": title,
            "status": status_code,
            "detail": detail,
            "instance": path,
        },
        status=status_code,
        content_type="application/problem+json",
    )
