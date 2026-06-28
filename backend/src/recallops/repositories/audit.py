import re
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from recallops.domain.models import MemoryOperation

_SENSITIVE_ERROR = re.compile(
    r"(?i)(authorization|x-api-key|cognee[_-]?api[_-]?key|bearer\s+\S+|sk-[a-z0-9])",
)


def _safe_error_category(error_detail: str | None) -> str | None:
    if error_detail is None:
        return None
    if _SENSITIVE_ERROR.search(error_detail):
        return "[REDACTED]"
    return error_detail[:100]


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def start(
        self,
        *,
        request_id: str,
        incident_id: str | None,
        trace_id: str | None,
        operation: str,
        dataset: str,
        target_id: str | None,
        estimated_tokens: int,
        started_at: datetime | None = None,
    ) -> MemoryOperation:
        record = MemoryOperation(
            request_id=request_id,
            incident_id=incident_id,
            trace_id=trace_id,
            operation=operation,
            dataset=dataset,
            target_id=target_id,
            started_at=started_at or datetime.now(UTC),
            success=False,
            estimated_tokens=estimated_tokens,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def finish(
        self,
        record: MemoryOperation,
        *,
        success: bool,
        error_detail: str | None = None,
        finished_at: datetime | None = None,
    ) -> None:
        completed_at = finished_at or datetime.now(UTC)
        duration = completed_at - record.started_at
        record.finished_at = completed_at
        record.duration_ms = max(0, round(duration.total_seconds() * 1000))
        record.success = success
        record.error_category = _safe_error_category(error_detail)
        await self._session.flush()
