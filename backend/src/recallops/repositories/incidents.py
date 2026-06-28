from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from recallops.domain.models import Incident, Observation


class IncidentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, incident_id: str) -> Incident | None:
        return await self._session.get(Incident, incident_id)

    async def list_incidents(self) -> list[Incident]:
        statement = select(Incident).order_by(Incident.started_at.desc())
        return list((await self._session.scalars(statement)).all())

    async def get_observation(self, observation_id: str) -> Observation | None:
        return await self._session.get(Observation, observation_id)

    async def observations(self, incident_id: str) -> list[Observation]:
        statement = (
            select(Observation)
            .where(Observation.incident_id == incident_id)
            .order_by(Observation.timestamp, Observation.id)
        )
        return list((await self._session.scalars(statement)).all())
