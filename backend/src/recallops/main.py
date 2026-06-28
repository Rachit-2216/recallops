from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.cors import CORSMiddleware

from recallops.api.demo import router as demo_router
from recallops.api.evidence import router as evidence_router
from recallops.api.health import router as health_router
from recallops.api.incidents import router as incidents_router
from recallops.config import Settings
from recallops.db import Base, create_session_factory
from recallops.errors import ERRORS_BY_STATUS, error_response, install_error_handlers
from recallops.logging import configure_logging, get_logger
from recallops.memory.contract import CogneeMemoryPort
from recallops.memory.fake import FakeCogneeAdapter
from recallops.services.credit_guard import CreditGuard
from recallops.services.demo import DemoService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


def create_app(
    settings: Settings | None = None,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    memory: CogneeMemoryPort | None = None,
    fixtures_dir: Path | None = None,
    credit_guard: CreditGuard | None = None,
    frontend_dist: Path | None = None,
) -> FastAPI:
    app_settings = settings or Settings()
    configure_logging()
    logger = get_logger()
    application = FastAPI(title="RecallOps", version="0.1.0")
    install_error_handlers(application)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[app_settings.public_origin],
        allow_credentials=True,
        allow_methods=["DELETE", "GET", "OPTIONS", "POST"],
        allow_headers=[
            "Content-Type",
            "X-Demo-Admin-Token",
            "X-Demo-Session",
        ],
        expose_headers=["X-Request-ID"],
    )
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
    application.state.mutation_counts = {}
    application.state.fixtures_dir = fixtures_dir or (
        Path(__file__).resolve().parents[3] / "demo" / "fixtures"
    )

    if app_settings.demo_bootstrap:
        async def bootstrap_synthetic_demo() -> None:
            if engine is not None:
                async with engine.begin() as connection:
                    await connection.run_sync(Base.metadata.create_all)
            async with session_factory() as session:
                await DemoService(
                    session=session,
                    memory=memory,
                    fixtures_dir=application.state.fixtures_dir,
                    dataset=app_settings.cognee_dataset,
                ).seed(force=isinstance(memory, FakeCogneeAdapter))

        application.router.add_event_handler("startup", bootstrap_synthetic_demo)

    if app_settings.e2e_mode:
        @application.post("/api/test/memory-failures", include_in_schema=False)
        async def set_fake_memory_failures(
            body: dict[str, list[str]],
        ) -> dict[str, list[str]]:
            if not isinstance(memory, FakeCogneeAdapter):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
            operations = set(body.get("operations", []))
            allowed = {
                "dataset_status",
                "forget",
                "health",
                "improve",
                "recall",
                "remember",
            }
            if not operations <= allowed:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                )
            memory.fail_operations = operations
            return {"operations": sorted(operations)}

    @application.middleware("http")
    async def add_request_id(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        started = perf_counter()
        request_id = str(uuid4())
        request.state.request_id = request_id
        path = request.url.path
        is_public_mutation = (
            app_settings.env == "production"
            and app_settings.demo_mode
            and request.method in {"DELETE", "POST"}
            and path.startswith("/api/")
            and not path.endswith("/recall")
        )
        response: Response
        if is_public_mutation:
            client_host = request.client.host if request.client is not None else "unknown"
            demo_session = request.headers.get("X-Demo-Session", client_host)
            mutation_counts: dict[str, tuple[float, int]] = (
                application.state.mutation_counts
            )
            window_started, mutation_count = mutation_counts.get(
                demo_session,
                (started, 0),
            )
            if started - window_started >= 60:
                window_started, mutation_count = started, 0
            if mutation_count >= 40:
                response = error_response(
                    request,
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    definition=ERRORS_BY_STATUS[429],
                )
            else:
                mutation_counts[demo_session] = (
                    window_started,
                    mutation_count + 1,
                )
                response = await call_next(request)
        else:
            response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "object-src 'none'; "
            "base-uri 'none'; "
            "frame-ancestors 'none'"
        )
        route = request.scope.get("route")
        route_template = getattr(route, "path", "unmatched")
        status_code = response.status_code
        logger.info(
            "http_request",
            request_id=request_id,
            route=route_template,
            method=request.method,
            status=status_code,
            duration_ms=round((perf_counter() - started) * 1000, 2),
            incident_id=request.path_params.get("incident_id"),
            trace_id=getattr(request.state, "trace_id", None),
            operation=getattr(request.state, "operation", None),
            error_category=(
                f"HTTP_{status_code}" if status_code >= 400 else None
            ),
        )
        return response

    application.include_router(health_router)
    application.include_router(demo_router)
    application.include_router(evidence_router)
    application.include_router(incidents_router)

    frontend_dist_path = frontend_dist or (
        Path(__file__).resolve().parents[3] / "frontend" / "dist"
    )
    if frontend_dist_path.is_dir():
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles

        assets = frontend_dist_path / "assets"
        if assets.is_dir():
            application.mount(
                "/assets",
                StaticFiles(directory=assets),
                name="frontend-assets",
            )

        @application.get("/{full_path:path}", include_in_schema=False)
        async def serve_frontend(full_path: str) -> FileResponse:
            if full_path.startswith("api/"):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
            candidate = (frontend_dist_path / full_path).resolve()
            if (
                full_path
                and candidate.is_relative_to(frontend_dist_path.resolve())
                and candidate.is_file()
            ):
                return FileResponse(candidate)
            return FileResponse(frontend_dist_path / "index.html")

    return application


app = create_app()
