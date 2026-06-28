from fastapi import APIRouter, Request

from recallops.config import Settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict[str, object]:
    settings: Settings = request.app.state.settings
    memory_ready = settings.cognee_mode == "fake"
    return {
        "status": "ok",
        "database": "ok",
        "memory": {
            "mode": settings.cognee_mode,
            "reachable": memory_ready,
            "dataset_ready": memory_ready,
        },
        "demo_mode": settings.demo_mode,
        "credit_guard": {
            "protected_reserve": settings.cognee_protected_reserve,
        },
    }
