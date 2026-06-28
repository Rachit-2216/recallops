from typing import Literal, Protocol

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from recallops.domain.enums import VerificationState
from recallops.domain.models import (
    Incident,
    MemoryCandidate,
    Observation,
    RecallTrace,
    Resolution,
)
from recallops.memory.contract import RecallReference as MemoryReference
from recallops.repositories.audit import AuditRepository
from recallops.repositories.incidents import IncidentRepository
from recallops.repositories.recalls import RecallRepository
from recallops.services.credit_guard import CreditBudgetExceeded
from recallops.services.incidents import (
    DuplicateIncident,
    IncidentInputError,
    IncidentNotFound,
    IncidentService,
)
from recallops.services.lifecycle import (
    MemoryLifecycleService,
    ResolutionValidationError,
)
from recallops.services.recall import (
    MemoryProviderUnavailable,
    PartialMemory,
    RecallService,
    why_recalled_for,
)

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


class CreateIncidentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=5, max_length=12)
    title: str = Field(min_length=1, max_length=200)
    severity: str
    service: str = Field(min_length=1, max_length=100)


class ObserveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=4000)
    observation_id: str | None = None


class RecallRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=3, max_length=1000)
    include_trace: bool = True


class FeedbackRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace_id: str
    score: Literal[-1, 0, 1]
    explanation: str = Field(min_length=5, max_length=500)


class ResolveIncidentRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root_cause: str = Field(min_length=1, max_length=4000)
    mitigation: str = Field(min_length=1, max_length=4000)
    verification: str = Field(min_length=1, max_length=4000)
    trace_ids: list[str] = Field(min_length=1, max_length=20)
    confirmed_by_human: bool


class ReferenceLike(Protocol):
    @property
    def data_id(self) -> str: ...

    @property
    def chunk_id(self) -> str: ...

    @property
    def document_name(self) -> str: ...

    @property
    def snippet(self) -> str: ...


def _incident_payload(incident: Incident) -> dict[str, object]:
    return {
        "id": incident.id,
        "title": incident.title,
        "severity": incident.severity,
        "service": incident.service,
        "status": incident.status,
        "session_id": incident.session_id,
        "started_at": incident.started_at.isoformat(),
        "resolved_at": (
            incident.resolved_at.isoformat()
            if incident.resolved_at is not None
            else None
        ),
    }


def _observation_payload(observation: Observation) -> dict[str, object]:
    return {
        "id": observation.id,
        "incident_id": observation.incident_id,
        "timestamp": observation.timestamp.isoformat(),
        "source": observation.source,
        "content": observation.content,
        "memory_status": observation.memory_status,
        "memory_layer": "session",
        "retry_count": observation.retry_count,
    }


def _reference_payload(reference: ReferenceLike) -> dict[str, str]:
    return {
        "data_id": reference.data_id,
        "chunk_id": reference.chunk_id,
        "document_name": reference.document_name,
        "snippet": reference.snippet,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_incident(
    body: CreateIncidentRequest,
    request: Request,
) -> dict[str, object]:
    async with request.app.state.session_factory() as session:
        service = IncidentService(
            session=session,
            memory=request.app.state.memory,
        )
        try:
            incident = await service.create(
                incident_id=body.id,
                title=body.title,
                severity=body.severity,
                service=body.service,
            )
        except IncidentInputError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error
        except DuplicateIncident as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        return _incident_payload(incident)


@router.get("")
async def list_incidents(request: Request) -> dict[str, object]:
    async with request.app.state.session_factory() as session:
        incidents = await IncidentRepository(session).list_incidents()
        return {"items": [_incident_payload(incident) for incident in incidents]}


@router.get("/{incident_id}")
async def get_incident(incident_id: str, request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    async with request.app.state.session_factory() as session:
        repository = IncidentRepository(session)
        incident = await repository.get(incident_id)
        if incident is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        observations = await repository.observations(incident_id)
        recalls = list(
            (
                await session.scalars(
                    select(RecallTrace)
                    .where(RecallTrace.incident_id == incident_id)
                    .order_by(RecallTrace.created_at.desc()),
                )
            ).all(),
        )
        candidates = list(
            (
                await session.scalars(
                    select(MemoryCandidate)
                    .where(MemoryCandidate.incident_id == incident_id)
                    .order_by(MemoryCandidate.created_at),
                )
            ).all(),
        )
        resolution = await session.scalar(
            select(Resolution).where(Resolution.incident_id == incident_id),
        )
        return {
            "incident": _incident_payload(incident),
            "observations": [
                _observation_payload(observation) for observation in observations
            ],
            "recalls": [
                {
                    "trace_id": trace.id,
                    "answer": trace.answer,
                    "verification": trace.verification_state,
                }
                for trace in recalls
            ],
            "memory_candidates": [
                {
                    "id": candidate.id,
                    "content": candidate.content,
                    "state": candidate.state,
                    "data_id": candidate.evidence_data_id,
                }
                for candidate in candidates
            ],
            "resolution": (
                {
                    "root_cause": resolution.root_cause,
                    "mitigation": resolution.mitigation,
                    "verification": resolution.verification,
                    "promotion_state": resolution.promotion_state,
                }
                if resolution is not None
                else None
            ),
            "budget": {
                "estimated_remaining": settings.cognee_token_supply,
                "protected_reserve": settings.cognee_protected_reserve,
            },
        }


@router.post("/{incident_id}/observe", response_model=None)
async def observe_incident(
    incident_id: str,
    body: ObserveRequest,
    request: Request,
) -> dict[str, object] | JSONResponse:
    async with request.app.state.session_factory() as session:
        service = IncidentService(
            session=session,
            memory=request.app.state.memory,
        )
        try:
            observation = await service.observe(
                incident_id=incident_id,
                content=body.content,
                observation_id=body.observation_id,
            )
        except IncidentNotFound as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            ) from error
        except IncidentInputError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error

        payload = _observation_payload(observation)
        if observation.memory_status == "pending":
            return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=payload)
        return payload


@router.post("/{incident_id}/recall", response_model=None)
async def recall_incident(
    incident_id: str,
    body: RecallRequestBody,
    request: Request,
) -> dict[str, object] | JSONResponse:
    query = body.query.strip()
    if len(query) < 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="query must contain at least 3 non-whitespace characters",
        )
    client_host = request.client.host if request.client is not None else "unknown"
    demo_session = request.headers.get("X-Demo-Session", client_host)
    recall_counts: dict[str, int] = request.app.state.recall_counts
    current_count = recall_counts.get(demo_session, 0)
    if current_count >= 20:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demo recall limit reached. Reset the demo to continue.",
        )
    recall_counts[demo_session] = current_count + 1

    async with request.app.state.session_factory() as session:
        incident = await IncidentRepository(session).get(incident_id)
        if incident is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        service = RecallService(
            session=session,
            memory=request.app.state.memory,
            repository=RecallRepository(session),
            audit=AuditRepository(session),
            credit_guard=request.app.state.credit_guard,
            dataset=request.app.state.settings.cognee_dataset,
        )
        try:
            result = await service.ask(
                incident=incident,
                query=query,
                request_id=request.state.request_id,
            )
        except PartialMemory:
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "answer": None,
                    "verification": VerificationState.UNVERIFIED.value,
                    "partial_memory": True,
                    "no_result": False,
                },
            )
        except MemoryProviderUnavailable as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Memory provider unavailable",
            ) from error
        except CreditBudgetExceeded as error:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Protected Cognee reserve reached",
            ) from error

        return {
            "answer": result.answer,
            "verification": result.verification.value,
            "source": result.source,
            "search_type": result.search_type,
            "references": [
                _reference_payload(reference) for reference in result.references
            ],
            "trace_id": result.trace_id,
            "why_recalled": list(result.why_recalled),
            "no_result": result.no_result,
            "partial_memory": False,
        }


@router.get("/{incident_id}/recalls/{trace_id}")
async def get_recall_trace(
    incident_id: str,
    trace_id: str,
    request: Request,
) -> dict[str, object]:
    async with request.app.state.session_factory() as session:
        trace = await RecallRepository(session).get(trace_id)
        if trace is None or trace.incident_id != incident_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        references = tuple(
            MemoryReference(
                data_id=reference.data_id,
                chunk_id=reference.chunk_id,
                document_name=reference.document_name,
                snippet=reference.snippet,
            )
            for reference in trace.references
        )
        return {
            "trace_id": trace.id,
            "answer": trace.answer,
            "verification": trace.verification_state,
            "source": trace.source,
            "search_type": trace.search_type,
            "references": [
                _reference_payload(reference) for reference in references
            ],
            "why_recalled": list(why_recalled_for(references)),
            "latency_ms": trace.latency_ms,
        }


@router.post(
    "/{incident_id}/feedback",
    status_code=status.HTTP_201_CREATED,
)
async def record_feedback(
    incident_id: str,
    body: FeedbackRequestBody,
    request: Request,
) -> dict[str, object]:
    async with request.app.state.session_factory() as session:
        incident = await IncidentRepository(session).get(incident_id)
        if incident is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        service = MemoryLifecycleService(
            session=session,
            memory=request.app.state.memory,
            audit=AuditRepository(session),
            dataset=request.app.state.settings.cognee_dataset,
        )
        try:
            feedback = await service.record_feedback(
                incident=incident,
                trace_id=body.trace_id,
                score=body.score,
                explanation=body.explanation,
            )
        except ResolutionValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error
        except Exception as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Memory provider unavailable",
            ) from error
        return {
            "id": feedback.id,
            "trace_id": feedback.trace_id,
            "score": feedback.score,
            "explanation": feedback.explanation,
        }


@router.post("/{incident_id}/resolve", response_model=None)
async def resolve_incident(
    incident_id: str,
    body: ResolveIncidentRequestBody,
    request: Request,
) -> dict[str, object] | JSONResponse:
    async with request.app.state.session_factory() as session:
        incident = await IncidentRepository(session).get(incident_id)
        if incident is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        service = MemoryLifecycleService(
            session=session,
            memory=request.app.state.memory,
            audit=AuditRepository(session),
            dataset=request.app.state.settings.cognee_dataset,
        )
        try:
            resolution = await service.resolve_incident(
                incident=incident,
                root_cause=body.root_cause,
                mitigation=body.mitigation,
                verification=body.verification,
                trace_ids=body.trace_ids,
                confirmed_by_human=body.confirmed_by_human,
                request_id=request.state.request_id,
            )
        except ResolutionValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error

        payload: dict[str, object] = {
            "incident_id": incident.id,
            "incident_status": incident.status,
            "promotion_state": resolution.promotion_state,
            "root_cause": resolution.root_cause,
            "mitigation": resolution.mitigation,
            "verification": resolution.verification,
            "confirmed_at": (
                resolution.confirmed_at.isoformat()
                if resolution.confirmed_at is not None
                else None
            ),
            "trace_ids": body.trace_ids,
        }
        if resolution.promotion_state == "promotion_failed":
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=payload,
            )
        return payload
