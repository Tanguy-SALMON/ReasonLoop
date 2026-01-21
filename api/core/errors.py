"""
Custom exceptions and error handlers for the API
"""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class APIError(Exception):
    """Base API error"""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ValidationError(APIError):
    """Input validation failed"""

    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class NotFoundError(APIError):
    """Resource not found"""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ServiceError(APIError):
    """External service error (LLM, scraping, etc.)"""

    def __init__(self, message: str):
        super().__init__(message, status_code=503)


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle custom API errors"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.message,
            "status_code": exc.status_code,
        },
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "status_code": 500,
        },
    )
