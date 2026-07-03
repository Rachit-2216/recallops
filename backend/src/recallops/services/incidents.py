import re
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from recallops.domain.enums import IncidentSeverity
from recallops.domain.models import Incident, Observation
from recallops.memory.contract import CogneeMemoryPort
from recallops.repositories.incidents import IncidentRepository

INCIDENT_ID_PATTERN = re.compile(r"INC-[0-9]{1,8}\Z")


class IncidentServiceError(RuntimeError):
    pass


class IncidentInputError(IncidentServiceError):
    pass


class DuplicateIncident(IncidentServiceError):
    pass


class IncidentNotFound(IncidentServiceError):
    pass


class IncidentService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        memory: CogneeMemoryPort,
    ) -> None:
        self._session = session
        self._memory = memory
        self._repository = IncidentRepository(session)

    async def create(
        self,
        *,
        incident_id: str,
        title: str,
        severity: str,
        service: str,
    ) -> Incident:
        if INCIDENT_ID_PATTERN.fullmatch(incident_id) is None:
            raise IncidentInputError("incident ID must match INC-[0-9]{1,8}")
        clean_title = title.strip()
        clean_service = service.strip()
        if not 1 <= len(clean_title) <= 200:
            raise IncidentInputError("title must contain 1-200 characters")
        if not 1 <= len(clean_service) <= 100:
            raise IncidentInputError("service must contain 1-100 characters")
        try:
            IncidentSeverity(severity)
        except ValueError as error:
            raise IncidentInputError("severity must be SEV1, SEV2, or SEV3") from error
        if await self._repository.get(incident_id) is not None:
            raise DuplicateIncident(f"incident {incident_id} already exists")

        incident = Incident(
            id=incident_id,
            title=clean_title,
            severity=severity,
            service=clean_service,
            status="active",
            session_id=f"incident:{incident_id}",
            started_at=datetime.now(UTC),
        )
        self._session.add(incident)
        await self._session.commit()
        return incident

    async def observe(
        self,
        *,
        incident_id: str,
        content: str,
        observation_id: str | None = None,
    ) -> Observation:
        incident = await self._repository.get(incident_id)
        if incident is None:
            raise IncidentNotFound(f"incident {incident_id} was not found")
        clean_content = content.strip()
        if not 1 <= len(clean_content) <= 4000:
            raise IncidentInputError("observation must contain 1-4000 characters")

        observation = (
            await self._repository.get_observation(observation_id)
            if observation_id is not None
            else None
        )
        if observation is not None:
            if observation.incident_id != incident_id:
                raise IncidentInputError("observation does not belong to incident")
            if observation.memory_status != "pending":
                return observation
            observation.retry_count += 1
        else:
            observation = Observation(
                id=observation_id,
                incident_id=incident_id,
                timestamp=datetime.now(UTC),
                source="human",
                content=clean_content,
                memory_status="pending",
            )
            self._session.add(observation)
            await self._session.flush()

        try:
            receipt = await self._memory.remember_observation(
                session_id=incident.session_id,
                content=observation.content,
            )
        except Exception:
            observation.memory_status = "pending"
            await self._session.commit()
            return observation

        observation.memory_status = (
            "session_stored" if receipt.status in {"completed", "session_stored"} else "pending"
        )
        await self._session.commit()
        return observation
