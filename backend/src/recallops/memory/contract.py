from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class EvidencePayload:
    data_id: str
    name: str
    content: str | bytes
    dataset: str


@dataclass(frozen=True, slots=True)
class RememberReceipt:
    status: str
    data_id: str | None = None


@dataclass(frozen=True, slots=True)
class RecallRequest:
    query: str
    dataset: str
    session_id: str
    include_trace: bool = True
    only_context: bool = False


@dataclass(frozen=True, slots=True)
class RecallReference:
    data_id: str
    chunk_id: str
    document_name: str
    snippet: str


@dataclass(frozen=True, slots=True)
class RecallEntry:
    answer: str
    source: str
    search_type: str
    references: tuple[RecallReference, ...] = ()
    raw_kind: str = "dictionary"


@dataclass(frozen=True, slots=True)
class ImproveReceipt:
    status: str
    session_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ForgetReceipt:
    status: str
    data_id: str


@dataclass(frozen=True, slots=True)
class DatasetStatus:
    dataset: str
    ready: bool
    status: str


@dataclass(frozen=True, slots=True)
class MemoryHealth:
    reachable: bool
    mode: str


class CogneeMemoryPort(Protocol):
    async def remember_evidence(
        self,
        payload: EvidencePayload,
    ) -> RememberReceipt: ...

    async def remember_observation(
        self,
        session_id: str,
        content: str,
    ) -> RememberReceipt: ...

    async def recall(self, request: RecallRequest) -> list[RecallEntry]: ...

    async def improve_session(
        self,
        dataset: str,
        session_ids: list[str],
    ) -> ImproveReceipt: ...

    async def forget_evidence_item(
        self,
        dataset: str,
        data_id: str,
    ) -> ForgetReceipt: ...

    async def dataset_status(self, dataset: str) -> DatasetStatus: ...

    async def health(self) -> MemoryHealth: ...
