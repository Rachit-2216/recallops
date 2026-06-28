from dataclasses import asdict
from pathlib import PurePosixPath
from typing import Annotated
from urllib.parse import unquote, urlsplit
from uuid import uuid4

import httpx
from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from recallops.config import Settings
from recallops.domain.models import EvidenceItem
from recallops.repositories.audit import AuditRepository
from recallops.repositories.evidence import EvidenceRepository
from recallops.services.evidence import (
    LOCAL_LIMIT,
    EvidenceService,
    EvidenceTooLarge,
    MemoryIngestionFailed,
    PublicUploadDisabled,
    UnsupportedEvidenceType,
)
from recallops.services.lifecycle import (
    ForgetConfirmationMismatch,
    ForgetVerificationFailed,
    MemoryLifecycleService,
    MemoryProviderRejected,
    MemoryStateConflict,
)

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


class ForgetEvidenceRequest(BaseModel):
    confirmation: str = Field(min_length=1, max_length=300)
    verification_query: str = Field(min_length=3, max_length=1000)


class UrlEvidenceRequest(BaseModel):
    model_config = {"extra": "forbid"}

    url: str = Field(min_length=8, max_length=2000)
    name: str | None = Field(default=None, min_length=1, max_length=255)


def _item_payload(item: EvidenceItem) -> dict[str, object]:
    return {
        "data_id": item.data_id,
        "dataset": item.dataset,
        "name": item.name,
        "kind": item.kind,
        "source_uri": item.source_uri,
        "status": item.status,
        "content_hash": item.content_hash,
        "source_date": item.source_date.isoformat() if item.source_date else None,
        "is_stale": item.is_stale,
        "memory_layer": "permanent",
    }


@router.post("")
async def ingest_evidence(
    request: Request,
    file: Annotated[UploadFile, File()],
) -> JSONResponse:
    settings: Settings = request.app.state.settings
    public_demo = settings.env == "production" and settings.demo_mode
    if public_demo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Arbitrary uploads are disabled",
        )
    content = await file.read(LOCAL_LIMIT + 1)
    async with request.app.state.session_factory() as session:
        service = EvidenceService(
            session=session,
            memory=request.app.state.memory,
            dataset=settings.cognee_dataset,
            public_demo=False,
        )
        try:
            result = await service.ingest_upload(
                filename=file.filename or "upload",
                content_type=file.content_type or "application/octet-stream",
                content=content,
            )
        except EvidenceTooLarge as error:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=str(error),
            ) from error
        except UnsupportedEvidenceType as error:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=str(error),
            ) from error
        except PublicUploadDisabled as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error
        except MemoryIngestionFailed as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Memory provider unavailable",
            ) from error

        payload = {**_item_payload(result.item), "reused": result.reused}
    return JSONResponse(
        status_code=status.HTTP_200_OK if result.reused else status.HTTP_201_CREATED,
        content=payload,
    )


@router.post("/url")
async def ingest_evidence_url(
    body: UrlEvidenceRequest,
    request: Request,
) -> JSONResponse:
    from recallops.services.url_security import validate_safe_evidence_url

    settings: Settings = request.app.state.settings
    public_demo = settings.env == "production" and settings.demo_mode
    if public_demo or not settings.allow_url_ingestion:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="URL ingestion is disabled",
        )
    try:
        safe_url = await validate_safe_evidence_url(body.url)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsafe evidence URL",
        ) from error

    try:
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=httpx.Timeout(10.0),
        ) as client:
            async with client.stream("GET", safe_url) as response:
                if response.is_redirect:
                    raise ValueError("redirects are not accepted")
                response.raise_for_status()
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > 5 * 1024 * 1024:
                        raise EvidenceTooLarge("evidence exceeds size limit")
                content_type = response.headers.get(
                    "content-type",
                    "application/octet-stream",
                ).split(";", 1)[0]
    except EvidenceTooLarge as error:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Evidence exceeds size limit",
        ) from error
    except (httpx.HTTPError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Evidence URL could not be fetched safely",
        ) from error

    parsed = urlsplit(safe_url)
    filename = body.name or PurePosixPath(unquote(parsed.path)).name or "evidence.txt"
    async with request.app.state.session_factory() as session:
        service = EvidenceService(
            session=session,
            memory=request.app.state.memory,
            dataset=settings.cognee_dataset,
            public_demo=False,
        )
        try:
            result = await service.ingest_upload(
                filename=filename,
                content_type=content_type,
                content=bytes(content),
            )
        except UnsupportedEvidenceType as error:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported evidence type",
            ) from error
        except MemoryIngestionFailed as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Memory provider unavailable",
            ) from error
    return JSONResponse(
        status_code=status.HTTP_200_OK if result.reused else status.HTTP_201_CREATED,
        content={**_item_payload(result.item), "reused": result.reused},
    )


@router.get("")
async def list_evidence(request: Request) -> dict[str, object]:
    settings: Settings = request.app.state.settings
    async with request.app.state.session_factory() as session:
        items = await EvidenceRepository(session).list_for_dataset(
            settings.cognee_dataset,
        )
        return {"items": [_item_payload(item) for item in items]}


@router.get("/{data_id}")
async def get_evidence(data_id: str, request: Request) -> dict[str, object]:
    async with request.app.state.session_factory() as session:
        item = await EvidenceRepository(session).get(data_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        return _item_payload(item)


@router.get("/{data_id}/status")
async def get_evidence_status(
    data_id: str,
    request: Request,
) -> dict[str, object]:
    async with request.app.state.session_factory() as session:
        item = await EvidenceRepository(session).get(data_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        memory_status = await request.app.state.memory.dataset_status(item.dataset)
        return {
            "data_id": item.data_id,
            "local_status": item.status,
            "memory_status": memory_status.status if item.status == "ready" else item.status,
        }


@router.delete("/{data_id}")
async def forget_evidence(
    data_id: str,
    body: ForgetEvidenceRequest,
    request: Request,
) -> dict[str, object]:
    async with request.app.state.session_factory() as session:
        item = await EvidenceRepository(session).get(data_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        service = MemoryLifecycleService(
            session=session,
            memory=request.app.state.memory,
            audit=AuditRepository(session),
        )
        request_id = getattr(request.state, "request_id", str(uuid4()))
        try:
            result = await service.forget_evidence(
                item=item,
                confirmation=body.confirmation,
                verification_query=body.verification_query,
                request_id=request_id,
            )
        except ForgetConfirmationMismatch as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error
        except MemoryStateConflict as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        except (
            ForgetVerificationFailed,
            MemoryProviderRejected,
        ) as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Memory provider could not verify forgetting",
            ) from error

        return {
            **asdict(result),
            "status": item.status,
        }
