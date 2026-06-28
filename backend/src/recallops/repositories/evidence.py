from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from recallops.domain.models import EvidenceItem


class EvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, data_id: str) -> EvidenceItem | None:
        return await self._session.get(EvidenceItem, data_id)

    async def get_by_hash(
        self,
        *,
        dataset: str,
        content_hash: str,
    ) -> EvidenceItem | None:
        statement = select(EvidenceItem).where(
            EvidenceItem.dataset == dataset,
            EvidenceItem.content_hash == content_hash,
        )
        return cast(EvidenceItem | None, await self._session.scalar(statement))

    async def list_for_dataset(self, dataset: str) -> list[EvidenceItem]:
        statement = (
            select(EvidenceItem)
            .where(EvidenceItem.dataset == dataset)
            .order_by(EvidenceItem.created_at, EvidenceItem.name)
        )
        return list((await self._session.scalars(statement)).all())
