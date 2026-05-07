from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def error_response(status_code: int, error_code: str, message: str, details: Any | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error_code": error_code,
            "message": message,
            "details": details or {},
        },
    )


async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        return error_response(
            exc.status_code,
            exc.detail.get("error_code", "REQUEST_FAILED"),
            exc.detail.get("message", "Request failed"),
            exc.detail.get("details", {}),
        )
    if exc.status_code == 401:
        return error_response(401, "UNAUTHORIZED_DEVICE", "Unauthorized device credentials")
    if exc.status_code == 404:
        return error_response(404, "RESOURCE_NOT_FOUND", str(exc.detail))
    if exc.status_code == 429:
        return error_response(429, "RATE_LIMITED", str(exc.detail))
    return error_response(exc.status_code, "REQUEST_FAILED", str(exc.detail))


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(
        422,
        "INVALID_PAYLOAD",
        "Payload validation failed",
        {"errors": exc.errors()},
    )
