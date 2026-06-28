from fastapi import APIRouter, Request

from recallops.config import Settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict[str, object]:
    settings: Settings = request.app.state.settings
    try:
        memory_health = await request.app.state.memory.health()
        dataset = await request.app.state.memory.dataset_status(
            settings.cognee_dataset,
        )
        memory_reachable = memory_health.reachable
        dataset_ready = dataset.ready
    except Exception:
        memory_reachable = False
        dataset_ready = False
    return {
        "status": "ok" if memory_reachable else "degraded",
        "database": "ok",
        "memory": {
            "mode": settings.cognee_mode,
            "reachable": memory_reachable,
            "dataset_ready": dataset_ready,
        },
        "demo_mode": settings.demo_mode,
        "credit_guard": {
            "protected_reserve": settings.cognee_protected_reserve,
        },
    }
