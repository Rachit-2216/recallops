from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.middleware.base import RequestResponseEndpoint

from recallops.api.demo import router as demo_router
from recallops.api.evidence import router as evidence_router
from recallops.api.health import router as health_router
from recallops.api.incidents import router as incidents_router
from recallops.config import Settings
from recallops.db import create_session_factory
from recallops.errors import install_error_handlers
from recallops.memory.contract import CogneeMemoryPort
from recallops.memory.fake import FakeCogneeAdapter
from recallops.services.credit_guard import CreditGuard

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


def create_app(
    settings: Settings | None = None,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    memory: CogneeMemoryPort | None = None,
    fixtures_dir: Path | None = None,
    credit_guard: CreditGuard | None = None,
) -> FastAPI:
    app_settings = settings or Settings()
    application = FastAPI(title="RecallOps", version="0.1.0")
    install_error_handlers(application)
    application.state.settings = app_settings
    engine: AsyncEngine | None = None
    if session_factory is None:
        engine, session_factory = create_session_factory(
            app_settings.database_url,
        )
    application.state.engine = engine
    application.state.session_factory = session_factory
    if memory is None:
        if app_settings.cognee_mode == "fake":
            memory = FakeCogneeAdapter()
        else:
            from recallops.memory.cognee_cloud import CogneeCloudAdapter

            if (
                app_settings.cognee_base_url is None
                or app_settings.cognee_api_key is None
            ):
                raise ValueError("live Cognee mode requires cloud configuration")
            memory = CogneeCloudAdapter(
                base_url=app_settings.cognee_base_url,
                api_key=app_settings.cognee_api_key.get_secret_value(),
            )
    application.state.memory = memory
    application.state.credit_guard = credit_guard or CreditGuard(
        supply=app_settings.cognee_token_supply,
        protected_reserve=app_settings.cognee_protected_reserve,
    )
    application.state.recall_counts = {}
    application.state.fixtures_dir = fixtures_dir or (
        Path(__file__).resolve().parents[3] / "demo" / "fixtures"
    )

    @application.middleware("http")
    async def add_request_id(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    application.include_router(health_router)
    application.include_router(demo_router)
    application.include_router(evidence_router)
    application.include_router(incidents_router)
    return application


app = create_app()
