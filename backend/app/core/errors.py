from typing import Any

from fastapi import HTTPException


class AppError(HTTPException):
    """Base application error producing the standard {code, message, details} error envelope."""

    def __init__(self, status_code: int, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(status_code=status_code, detail={"code": code, "message": message, "details": details or {}})


class NotFoundError(AppError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(404, code, message, details)


class ConflictError(AppError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(409, code, message, details)


class ValidationAppError(AppError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(422, code, message, details)
