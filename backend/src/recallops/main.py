from uuid import uuid4

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import RequestResponseEndpoint

from recallops.api.health import router as health_router
from recallops.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    application = FastAPI(title="RecallOps", version="0.1.0")
    application.state.settings = app_settings

    @application.middleware("http")
    async def add_request_id(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Request-ID"] = str(uuid4())
        return response

    application.include_router(health_router)
    return application


app = create_app()
