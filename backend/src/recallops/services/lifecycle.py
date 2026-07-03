import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from recallops.domain.models import EvidenceItem, Feedback, Incident, Resolution
from recallops.memory.contract import CogneeMemoryPort, RecallEntry, RecallRequest
from recallops.repositories.audit import AuditRepository
from recallops.repositories.recalls import RecallRepository


class MemoryLifecycleError(RuntimeError):
    pass


class ForgetConfirmationMismatch(MemoryLifecycleError):
    pass


class ForgetVerificationFailed(MemoryLifecycleError):
    pass


class MemoryStateConflict(MemoryLifecycleError):
    pass


class MemoryProviderRejected(MemoryLifecycleError):
    pass


class ResolutionValidationError(MemoryLifecycleError):
    pass


@dataclass(frozen=True, slots=True)
class ForgetResult:
    data_id: str
    before_reference_found: bool
    after_reference_found: bool


def _contains_reference(entries: list[RecallEntry], data_id: str) -> bool:
    return any(reference.data_id == data_id for entry in entries for reference in entry.references)


class MemoryLifecycleService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        memory: CogneeMemoryPort,
        audit: AuditRepository,
        dataset: str = "recallops_evidence_v1",
    ) -> None:
        self._session = session
        self._memory = memory
        self._audit = audit
        self._dataset = dataset

    async def forget_evidence(
        self,
        *,
        item: EvidenceItem,
        confirmation: str,
        verification_query: str,
        request_id: str,
    ) -> ForgetResult:
        if item.status != "ready":
            raise MemoryStateConflict("only ready permanent evidence can be forgotten")
        expected_confirmation = f"FORGET {item.name}"
        if confirmation != expected_confirmation:
            raise ForgetConfirmationMismatch("forget confirmation did not match")

        operation = await self._audit.start(
            request_id=request_id,
            incident_id=None,
            trace_id=None,
            operation="forget",
            dataset=item.dataset,
            target_id=item.data_id,
            estimated_tokens=10_000,
        )
        request = RecallRequest(
            query=verification_query,
            dataset=item.dataset,
            session_id="incident:forget-verification",
            include_trace=True,
        )
        try:
            before_entries = await self._memory.recall(request)
            before_reference_found = _contains_reference(
                before_entries,
                item.data_id,
            )
            receipt = await self._memory.forget_evidence_item(
                item.dataset,
                item.data_id,
            )
            if receipt.status != "deleted":
                raise MemoryProviderRejected("forget_provider_rejected")
            after_entries = await self._memory.recall(request)
            after_reference_found = _contains_reference(
                after_entries,
                item.data_id,
            )
            if after_reference_found:
                raise ForgetVerificationFailed("forget_verification_failed")
        except Exception as error:
            if isinstance(error, ForgetVerificationFailed):
                category = "forget_verification_failed"
            elif isinstance(error, MemoryProviderRejected):
                category = "forget_provider_rejected"
            else:
                category = "memory_provider_unavailable"
            await self._audit.finish(
                operation,
                success=False,
                error_detail=category,
            )
            await self._session.commit()
            raise

        item.status = "forgotten"
        item.forgotten_at = datetime.now(UTC)
        await self._audit.finish(operation, success=True)
        await self._session.commit()
        return ForgetResult(
            data_id=item.data_id,
            before_reference_found=before_reference_found,
            after_reference_found=after_reference_found,
        )

    async def record_feedback(
        self,
        *,
        incident: Incident,
        trace_id: str,
        score: int,
        explanation: str,
    ) -> Feedback:
        if score not in {-1, 0, 1}:
            raise ResolutionValidationError("feedback score must be -1, 0, or 1")
        clean_explanation = explanation.strip()
        if not 5 <= len(clean_explanation) <= 500:
            raise ResolutionValidationError(
                "feedback explanation must contain 5-500 characters",
            )
        trace = await RecallRepository(self._session).get(trace_id)
        if trace is None or trace.incident_id != incident.id:
            raise ResolutionValidationError("trace does not belong to incident")

        feedback = Feedback(
            incident_id=incident.id,
            trace_id=trace_id,
            score=score,
            explanation=clean_explanation,
        )
        self._session.add(feedback)
        await self._session.flush()
        await self._memory.remember_observation(
            session_id=incident.session_id,
            content=(f"Human feedback score {score} for trace {trace_id}: {clean_explanation}"),
        )
        await self._session.commit()
        return feedback

    async def resolve_incident(
        self,
        *,
        incident: Incident,
        root_cause: str,
        mitigation: str,
        verification: str,
        trace_ids: list[str],
        confirmed_by_human: bool,
        request_id: str,
    ) -> Resolution:
        clean_root_cause = root_cause.strip()
        clean_mitigation = mitigation.strip()
        clean_verification = verification.strip()
        if not clean_root_cause:
            raise ResolutionValidationError("root cause is required")
        if not clean_mitigation:
            raise ResolutionValidationError("mitigation is required")
        if not clean_verification:
            raise ResolutionValidationError("verification is required")
        if not confirmed_by_human:
            raise ResolutionValidationError("human confirmation is required")
        if not trace_ids:
            raise ResolutionValidationError("at least one referenced trace is required")

        recall_repository = RecallRepository(self._session)
        for trace_id in trace_ids:
            trace = await recall_repository.get(trace_id)
            if (
                trace is None
                or trace.incident_id != incident.id
                or trace.verification_state != "referenced"
            ):
                raise ResolutionValidationError(
                    "every resolution trace must be referenced and belong to the incident",
                )

        resolution = await self._session.scalar(
            select(Resolution).where(Resolution.incident_id == incident.id),
        )
        now = datetime.now(UTC)
        if resolution is None:
            resolution = Resolution(incident_id=incident.id)
            self._session.add(resolution)
        resolution.root_cause = clean_root_cause
        resolution.mitigation = clean_mitigation
        resolution.verification = clean_verification
        resolution.confirmed_by_human = True
        resolution.confirmed_at = now
        resolution.trace_ids_json = json.dumps(trace_ids)
        resolution.promotion_state = "promotion_pending"
        incident.status = "mitigated"
        await self._session.commit()

        operation = await self._audit.start(
            request_id=request_id,
            incident_id=incident.id,
            trace_id=trace_ids[0],
            operation="improve",
            dataset=self._dataset,
            target_id=incident.session_id,
            estimated_tokens=300_000,
        )
        compact_resolution = (
            f"Verified resolution for {incident.id}: "
            f"Root cause: {clean_root_cause} "
            f"Mitigation: {clean_mitigation} "
            f"Verification: {clean_verification}"
        )
        try:
            remembered = await self._memory.remember_observation(
                session_id=incident.session_id,
                content=compact_resolution,
            )
            if remembered.status not in {"completed", "session_stored"}:
                raise MemoryProviderRejected("resolution_session_remember_failed")
            improved = await self._memory.improve_session(
                dataset=self._dataset,
                session_ids=[incident.session_id],
            )
            if improved.status != "completed":
                raise MemoryProviderRejected("improve_provider_rejected")
        except Exception:
            resolution.promotion_state = "promotion_failed"
            incident.status = "mitigated"
            await self._audit.finish(
                operation,
                success=False,
                error_detail="improve_failed",
            )
            await self._session.commit()
            return resolution

        resolution.promotion_state = "promoted"
        resolution.improve_operation_id = operation.id
        incident.status = "resolved"
        incident.resolved_at = now
        promoted_data_id = str(
            uuid5(
                NAMESPACE_URL,
                f"{self._dataset}:{incident.session_id}:resolution",
            ),
        )
        promoted_item = await self._session.get(EvidenceItem, promoted_data_id)
        if promoted_item is None:
            incident_slug = incident.id.lower()
            promoted_item = EvidenceItem(
                data_id=promoted_data_id,
                dataset=self._dataset,
                name=f"verified-resolution-{incident_slug}.md",
                kind="memory_candidate",
                status="ready",
                content_hash=(
                    f"sha256:{hashlib.sha256(compact_resolution.encode('utf-8')).hexdigest()}"
                ),
            )
            self._session.add(promoted_item)
        await self._audit.finish(operation, success=True)
        await self._session.commit()
        return resolution
