"""
Shared service exception hierarchy.

All service-layer code should raise these exceptions instead of HTTP exceptions.
Views/serializers catch these and translate to appropriate HTTP responses.
"""


class ServiceError(Exception):
    """Base exception for all service-layer errors."""

    def __init__(self, message="A service error occurred", code=None):
        self.message = message
        self.code = code
        super().__init__(self.message)


class NotFoundError(ServiceError):
    """Raised when a requested resource does not exist."""

    def __init__(self, message="Resource not found", code="not_found"):
        super().__init__(message=message, code=code)


class PermissionDeniedError(ServiceError):
    """Raised when the user lacks permission for the requested action."""

    def __init__(self, message="Permission denied", code="permission_denied"):
        super().__init__(message=message, code=code)


class ValidationError(ServiceError):
    """Raised when input data fails validation rules."""

    def __init__(self, message="Validation failed", code="validation_error", errors=None):
        self.errors = errors or {}
        super().__init__(message=message, code=code)


class ConflictError(ServiceError):
    """Raised when an operation conflicts with current state (e.g., duplicate)."""

    def __init__(self, message="Conflict", code="conflict"):
        super().__init__(message=message, code=code)
