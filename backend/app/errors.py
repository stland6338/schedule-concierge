from fastapi import status

class BaseAppException(Exception):
    def __init__(self, code: str, message: str, http_status: int):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)

class NotFoundError(BaseAppException):
    def __init__(self, code: str, message: str):
        super().__init__(code, message, status.HTTP_404_NOT_FOUND)

class ConflictError(BaseAppException):
    def __init__(self, code: str, message: str):
        super().__init__(code, message, status.HTTP_409_CONFLICT)

class ValidationAppError(BaseAppException):
    def __init__(self, code: str, message: str):
        super().__init__(code, message, status.HTTP_400_BAD_REQUEST)

class InternalServerError(BaseAppException):
    def __init__(self, message: str = "internal error"):
        super().__init__("INTERNAL_ERROR", message, status.HTTP_500_INTERNAL_SERVER_ERROR)
