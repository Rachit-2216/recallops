import hashlib
from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from recallops.domain.models import EvidenceItem
from recallops.memory.contract import CogneeMemoryPort, EvidencePayload
from recallops.repositories.evidence import EvidenceRepository

LOCAL_LIMIT = 5 * 1024 * 1024
PUBLIC_LIMIT = 1024 * 1024
ALLOWED_TYPES = {
    ".md": {"text/markdown", "text/plain"},
    ".txt": {"text/plain"},
    ".json": {"application/json"},
    ".log": {"text/plain"},
    ".pdf": {"application/pdf"},
}
EVIDENCE_KINDS = {
    ".md": "note",
    ".txt": "note",
    ".json": "deploy",
    ".log": "log",
    ".pdf": "postmortem",
}
DANGEROUS_SUFFIXES = {
    ".bat",
    ".cmd",
    ".com",
    ".exe",
    ".js",
    ".msi",
    ".ps1",
    ".scr",
    ".sh",
}


class EvidenceValidationError(ValueError):
    """Base class for safe evidence validation failures."""


class EvidenceTooLarge(EvidenceValidationError):
    pass


class UnsupportedEvidenceType(EvidenceValidationError):
    pass


class PublicUploadDisabled(EvidenceValidationError):
    pass


class MemoryIngestionFailed(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class IngestResult:
    item: EvidenceItem
    reused: bool


def _safe_name(filename: str) -> str:
    normalized = filename.replace("\\", "/")
    return normalized.rsplit("/", 1)[-1]


def _validate_type(filename: str, content_type: str) -> str:
    lowered = filename.casefold()
    matching_extension = next(
        (extension for extension in ALLOWED_TYPES if lowered.endswith(extension)),
        None,
    )
    if matching_extension is None:
        raise UnsupportedEvidenceType("unsupported evidence extension")
    prefix = lowered[: -len(matching_extension)]
    if any(prefix.endswith(suffix) for suffix in DANGEROUS_SUFFIXES):
        raise UnsupportedEvidenceType("dangerous double extension")
    if content_type.casefold() not in ALLOWED_TYPES[matching_extension]:
        raise UnsupportedEvidenceType("content type does not match extension")
    return matching_extension


class EvidenceService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        memory: CogneeMemoryPort,
        dataset: str,
        public_demo: bool,
    ) -> None:
        self._session = session
        self._memory = memory
        self._dataset = dataset
        self._public_demo = public_demo
        self._repository = EvidenceRepository(session)

    async def ingest_upload(
        self,
        *,
        filename: str,
        content_type: str,
        content: bytes,
        allow_public_fixture: bool = False,
    ) -> IngestResult:
        if self._public_demo and not allow_public_fixture:
            raise PublicUploadDisabled("arbitrary uploads are disabled")
        limit = PUBLIC_LIMIT if self._public_demo else LOCAL_LIMIT
        if len(content) > limit:
            limit_label = "1 MB" if self._public_demo else "5 MB"
            raise EvidenceTooLarge(f"evidence exceeds the {limit_label} limit")

        display_name = _safe_name(filename)
        extension = _validate_type(display_name, content_type)
        digest = hashlib.sha256(content).hexdigest()
        content_hash = f"sha256:{digest}"
        existing = await self._repository.get_by_hash(
            dataset=self._dataset,
            content_hash=content_hash,
        )
        if existing is not None:
            return IngestResult(item=existing, reused=True)

        data_id = str(uuid5(NAMESPACE_URL, f"{self._dataset}:{digest}"))
        item = EvidenceItem(
            data_id=data_id,
            dataset=self._dataset,
            name=display_name,
            kind=EVIDENCE_KINDS[extension],
            status="processing",
            content_hash=content_hash,
        )
        self._session.add(item)
        await self._session.flush()
        try:
            receipt = await self._memory.remember_evidence(
                EvidencePayload(
                    data_id=data_id,
                    name=display_name,
                    content=content,
                    dataset=self._dataset,
                ),
            )
        except Exception as error:
            item.status = "failed"
            await self._session.commit()
            raise MemoryIngestionFailed("memory provider rejected evidence") from error

        if receipt.status not in {"completed", "running"}:
            item.status = "failed"
            await self._session.commit()
            raise MemoryIngestionFailed("memory provider did not index evidence")
        item.status = "ready"
        await self._session.commit()
        return IngestResult(item=item, reused=False)
