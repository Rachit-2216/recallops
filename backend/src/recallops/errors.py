from dataclasses import dataclass
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


@dataclass(frozen=True, slots=True)
class ErrorDefinition:
    code: str
    message: str
    retryable: bool = False


ERRORS_BY_STATUS = {
    400: ErrorDefinition("BAD_REQUEST", "The request could not be processed."),
    401: ErrorDefinition("UNAUTHORIZED", "Authentication is required."),
    403: ErrorDefinition("FORBIDDEN", "This operation is not available."),
    404: ErrorDefinition("NOT_FOUND", "The requested resource was not found."),
    405: ErrorDefinition("METHOD_NOT_ALLOWED", "This request method is not supported."),
    409: ErrorDefinition("CONFLICT", "The requested state conflicts with current state."),
    413: ErrorDefinition("PAYLOAD_TOO_LARGE", "The supplied evidence is too large."),
    415: ErrorDefinition(
        "UNSUPPORTED_MEDIA_TYPE",
        "The supplied evidence type is not supported.",
    ),
    422: ErrorDefinition("VALIDATION_ERROR", "The supplied request is invalid."),
    429: ErrorDefinition(
        "RATE_LIMITED",
        "The request limit was reached. Retry later.",
        retryable=True,
    ),
    503: ErrorDefinition(
        "MEMORY_PROVIDER_UNAVAILABLE",
        "Memory is temporarily unavailable. Your observation is saved locally.",
        retryable=True,
    ),
}
INTERNAL_ERROR = ErrorDefinition(
    "INTERNAL_ERROR",
    "The request could not be completed.",
    retryable=True,
)


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", uuid4()))


def error_response(
    request: Request,
    *,
    status_code: int,
    definition: ErrorDefinition,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": definition.code,
                "message": definition.message,
                "retryable": definition.retryable,
                "request_id": _request_id(request),
            },
        },
    )


def install_error_handlers(application: FastAPI) -> None:
    @application.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        request: Request,
        exception: StarletteHTTPException,
    ) -> JSONResponse:
        definition = ERRORS_BY_STATUS.get(exception.status_code, INTERNAL_ERROR)
        return error_response(
            request,
            status_code=exception.status_code,
            definition=definition,
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        _exception: RequestValidationError,
    ) -> JSONResponse:
        return error_response(
            request,
            status_code=422,
            definition=ERRORS_BY_STATUS[422],
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request,
        _exception: Exception,
    ) -> JSONResponse:
        return error_response(
            request,
            status_code=500,
            definition=INTERNAL_ERROR,
        )
