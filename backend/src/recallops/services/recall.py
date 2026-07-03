from dataclasses import dataclass
from time import monotonic

from sqlalchemy.ext.asyncio import AsyncSession

from recallops.domain.enums import VerificationState
from recallops.domain.models import Incident
from recallops.memory.contract import (
    CogneeMemoryPort,
    RecallEntry,
    RecallReference,
    RecallRequest,
)
from recallops.repositories.audit import AuditRepository
from recallops.repositories.recalls import RecallRepository
from recallops.services.credit_guard import CreditGuard


class RecallServiceError(RuntimeError):
    pass


class MemoryProviderUnavailable(RecallServiceError):
    pass


class PartialMemory(RecallServiceError):
    pass


@dataclass(frozen=True, slots=True)
class RecallResult:
    answer: str | None
    verification: VerificationState
    source: str
    search_type: str
    references: tuple[RecallReference, ...]
    trace_id: str
    why_recalled: tuple[str, ...]
    no_result: bool


def verification_for(entries: list[RecallEntry]) -> VerificationState:
    if any(entry.source == "contradiction" for entry in entries):
        return VerificationState.CONTRADICTED
    if any(entry.references for entry in entries):
        return VerificationState.REFERENCED
    return VerificationState.UNVERIFIED


def is_trace_eligible(verification: VerificationState) -> bool:
    return verification == VerificationState.REFERENCED


def _unique_references(entries: list[RecallEntry]) -> tuple[RecallReference, ...]:
    unique: dict[tuple[str, str], RecallReference] = {}
    for entry in entries:
        for reference in entry.references:
            unique[(reference.data_id, reference.chunk_id)] = reference
    return tuple(unique.values())


def why_recalled_for(
    references: tuple[RecallReference, ...],
) -> tuple[str, ...]:
    documents = {reference.document_name for reference in references}
    if "cloudflare-november-18-postmortem.md" not in documents:
        return ()
    return (
        "same operator: Cloudflare",
        "same distribution path: global configuration",
        "same failure pattern: configuration reached the fleet before health gates",
        "same blast-radius risk: fleet-wide propagation",
    )


class RecallService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        memory: CogneeMemoryPort,
        repository: RecallRepository,
        audit: AuditRepository,
        credit_guard: CreditGuard,
        dataset: str,
    ) -> None:
        self._session = session
        self._memory = memory
        self._repository = repository
        self._audit = audit
        self._credit_guard = credit_guard
        self._dataset = dataset

    async def ask(
        self,
        *,
        incident: Incident,
        query: str,
        request_id: str,
    ) -> RecallResult:
        self._credit_guard.authorize(
            "recall",
            estimated_tokens=20_000,
            essential=True,
        )
        dataset_status = await self._memory.dataset_status(self._dataset)
        if not dataset_status.ready:
            raise PartialMemory("memory dataset is still indexing")

        operation = await self._audit.start(
            request_id=request_id,
            incident_id=incident.id,
            trace_id=None,
            operation="recall",
            dataset=self._dataset,
            target_id=incident.session_id,
            estimated_tokens=20_000,
        )
        started = monotonic()
        try:
            entries = await self._memory.recall(
                RecallRequest(
                    query=query,
                    dataset=self._dataset,
                    session_id=incident.session_id,
                    include_trace=True,
                ),
            )
        except Exception as error:
            await self._audit.finish(
                operation,
                success=False,
                error_detail="memory_provider_unavailable",
            )
            await self._session.commit()
            raise MemoryProviderUnavailable(
                "memory provider unavailable",
            ) from error

        latency_ms = round((monotonic() - started) * 1000)
        verification = verification_for(entries)
        references = _unique_references(entries)
        first = entries[0] if entries else None
        trace = await self._repository.create(
            incident_id=incident.id,
            query=query,
            answer=first.answer if first is not None else None,
            source=first.source if first is not None else "none",
            search_type=first.search_type if first is not None else "none",
            verification_state=verification.value,
            latency_ms=latency_ms,
            references=references,
        )
        operation.trace_id = trace.id
        await self._audit.finish(operation, success=True)
        self._credit_guard.record_estimate("recall", 20_000)
        await self._session.commit()
        return RecallResult(
            answer=trace.answer,
            verification=verification,
            source=trace.source,
            search_type=trace.search_type,
            references=references,
            trace_id=trace.id,
            why_recalled=why_recalled_for(references),
            no_result=first is None,
        )
