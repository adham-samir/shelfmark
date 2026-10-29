"""Public application errors."""


class ApplicationError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class ProductNotFound(ApplicationError):
    def __init__(self) -> None:
        super().__init__(404, "product_not_found", "Product not found.")


class DependencyUnavailable(ApplicationError):
    def __init__(self, message: str = "A required catalog dependency is unavailable.") -> None:
        super().__init__(503, "dependency_unavailable", message)


class Unauthorized(ApplicationError):
    def __init__(self) -> None:
        super().__init__(401, "unauthorized", "Authentication is required.")


class TooManyRequests(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            429,
            "rate_limited",
            "Too many sign-in attempts. Wait five minutes and try again.",
        )


class Forbidden(ApplicationError):
    def __init__(self) -> None:
        super().__init__(403, "forbidden", "The required capability is not granted.")


class ResourceNotFound(ApplicationError):
    def __init__(self, message: str = "Resource not found.") -> None:
        super().__init__(404, "not_found", message)


class Conflict(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(409, "conflict", message)


class InvalidInput(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(422, "invalid_input", message)


class UnsupportedMedia(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(415, "unsupported_media", message)


class PayloadTooLarge(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(413, "payload_too_large", message)

