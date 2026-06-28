from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from recallops.db import Base
from recallops.memory.fake import FakeCogneeAdapter
from recallops.services.evidence import (
    EvidenceService,
    EvidenceTooLarge,
    PublicUploadDisabled,
    UnsupportedEvidenceType,
)

DATASET = "recallops_evidence_v1"


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as database_session:
        yield database_session
    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("runbook.md", "text/markdown"),
        ("notes.txt", "text/plain"),
        ("deploy.json", "application/json"),
        ("errors.log", "text/plain"),
        ("postmortem.pdf", "application/pdf"),
    ],
)
async def test_accepts_supported_evidence_types(
    session: AsyncSession,
    filename: str,
    content_type: str,
) -> None:
    service = EvidenceService(
        session=session,
        memory=FakeCogneeAdapter(),
        dataset=DATASET,
        public_demo=False,
    )

    result = await service.ingest_upload(
        filename=filename,
        content_type=content_type,
        content=b"synthetic evidence",
    )

    assert result.item.name == filename
    assert result.item.status == "ready"
    assert result.reused is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename",
    ["payload.exe", "runbook.exe.md", "notes.md.exe"],
)
async def test_rejects_executable_and_double_extension_names(
    session: AsyncSession,
    filename: str,
) -> None:
    service = EvidenceService(
        session=session,
        memory=FakeCogneeAdapter(),
        dataset=DATASET,
        public_demo=False,
    )

    with pytest.raises(UnsupportedEvidenceType):
        await service.ingest_upload(
            filename=filename,
            content_type="text/markdown",
            content=b"not executable content",
        )


@pytest.mark.asyncio
async def test_enforces_local_and_public_size_limits(
    session: AsyncSession,
) -> None:
    local = EvidenceService(
        session=session,
        memory=FakeCogneeAdapter(),
        dataset=DATASET,
        public_demo=False,
    )
    public = EvidenceService(
        session=session,
        memory=FakeCogneeAdapter(),
        dataset=DATASET,
        public_demo=True,
    )

    with pytest.raises(EvidenceTooLarge, match="5 MB"):
        await local.ingest_upload(
            filename="large.md",
            content_type="text/markdown",
            content=b"x" * (5 * 1024 * 1024 + 1),
        )
    with pytest.raises(EvidenceTooLarge, match="1 MB"):
        await public.ingest_upload(
            filename="large.md",
            content_type="text/markdown",
            content=b"x" * (1024 * 1024 + 1),
            allow_public_fixture=True,
        )


@pytest.mark.asyncio
async def test_public_demo_rejects_arbitrary_uploads(
    session: AsyncSession,
) -> None:
    service = EvidenceService(
        session=session,
        memory=FakeCogneeAdapter(),
        dataset=DATASET,
        public_demo=True,
    )

    with pytest.raises(PublicUploadDisabled):
        await service.ingest_upload(
            filename="notes.md",
            content_type="text/markdown",
            content=b"arbitrary",
        )


@pytest.mark.asyncio
async def test_identical_content_reuses_item_without_memory_call(
    session: AsyncSession,
) -> None:
    memory = FakeCogneeAdapter()
    service = EvidenceService(
        session=session,
        memory=memory,
        dataset=DATASET,
        public_demo=False,
    )

    first = await service.ingest_upload(
        filename="first-name.md",
        content_type="text/markdown",
        content=b"same content",
    )
    second = await service.ingest_upload(
        filename="second-name.md",
        content_type="text/markdown",
        content=b"same content",
    )

    assert second.item.data_id == first.item.data_id
    assert second.reused is True
    assert memory.operation_counts["remember"] == 1


@pytest.mark.asyncio
async def test_filename_is_display_only_and_cannot_select_a_path(
    session: AsyncSession,
) -> None:
    service = EvidenceService(
        session=session,
        memory=FakeCogneeAdapter(),
        dataset=DATASET,
        public_demo=False,
    )

    result = await service.ingest_upload(
        filename=r"..\..\safe-note.md",
        content_type="text/markdown",
        content=b"safe",
    )

    assert result.item.name == "safe-note.md"
