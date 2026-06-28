import secrets
from dataclasses import asdict

from fastapi import APIRouter, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from recallops.config import Settings
from recallops.services.demo import DemoService

router = APIRouter(prefix="/api/demo", tags=["demo"])


def _service(request: Request, session: AsyncSession) -> DemoService:
    return DemoService(
        session=session,
        memory=request.app.state.memory,
        fixtures_dir=request.app.state.fixtures_dir,
        dataset=request.app.state.settings.cognee_dataset,
    )


@router.post("/reset")
async def reset_demo(request: Request) -> dict[str, object]:
    settings: Settings = request.app.state.settings
    if not settings.demo_mode and settings.env != "local":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    async with request.app.state.session_factory() as session:
        result = await _service(request, session).reset()
    return {**asdict(result), "synthetic": True}


@router.post("/seed")
async def seed_demo(
    request: Request,
    demo_admin_token: str | None = Header(
        default=None,
        alias="X-Demo-Admin-Token",
    ),
) -> dict[str, object]:
    settings: Settings = request.app.state.settings
    supplied = demo_admin_token or ""
    expected = settings.demo_admin_token.get_secret_value()
    if not secrets.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    async with request.app.state.session_factory() as session:
        result = await _service(request, session).seed()
    return asdict(result)
