from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from recallops.domain.models import RecallReference, RecallTrace
from recallops.memory.contract import RecallReference as MemoryReference


class RecallRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        incident_id: str,
        query: str,
        answer: str | None,
        source: str,
        search_type: str,
        verification_state: str,
        latency_ms: int,
        references: tuple[MemoryReference, ...],
    ) -> RecallTrace:
        trace = RecallTrace(
            incident_id=incident_id,
            query=query,
            query_type="auto",
            source=source,
            search_type=search_type,
            answer=answer,
            verification_state=verification_state,
            latency_ms=latency_ms,
        )
        self._session.add(trace)
        await self._session.flush()
        for reference in references:
            self._session.add(
                RecallReference(
                    trace_id=trace.id,
                    data_id=reference.data_id,
                    chunk_id=reference.chunk_id,
                    document_name=reference.document_name,
                    snippet=reference.snippet,
                ),
            )
        await self._session.flush()
        return trace

    async def get(self, trace_id: str) -> RecallTrace | None:
        statement = (
            select(RecallTrace)
            .options(selectinload(RecallTrace.references))
            .where(RecallTrace.id == trace_id)
        )
        return cast(RecallTrace | None, await self._session.scalar(statement))
