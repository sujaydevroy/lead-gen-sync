"""Error responses in the shape the frontend services read: {"message": "..."}."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("app")


class ApiError(HTTPException):
    """Raise from services; becomes {"message": detail} with the given status."""

    def __init__(self, status_code: int, message: str, headers: dict[str, str] | None = None):
        super().__init__(status_code=status_code, detail=message, headers=headers)


def not_found(what: str) -> ApiError:
    return ApiError(404, f"{what} was not found.")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException):
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse({"message": message}, status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        errors = [
            {"field": ".".join(str(p) for p in err["loc"] if p not in ("body", "query", "form")), "message": err["msg"]}
            for err in exc.errors()
        ]
        first = errors[0] if errors else None
        message = f"{first['field']}: {first['message']}" if first and first["field"] else "Validation failed."
        return JSONResponse({"message": message, "errors": errors}, status_code=422)

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
        return JSONResponse({"message": "Internal server error."}, status_code=500)
