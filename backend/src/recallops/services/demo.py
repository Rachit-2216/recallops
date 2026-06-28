import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from recallops.domain.models import (
    EvidenceItem,
    Incident,
    MemoryCandidate,
    Observation,
)
from recallops.memory.contract import CogneeMemoryPort, EvidencePayload

DEMO_NAMESPACE = UUID("3d1d4c42-7e30-5e58-9e85-301ea55efcc1")
EVIDENCE_FIXTURES = {
    "postmortem-inc-1842.md": ("postmortem", False, "2026-05-14T00:00:00Z"),
    "checkout-runbook-v3.md": ("runbook", False, "2026-06-20T00:00:00Z"),
    "stale-cache-reset-rule.md": ("runbook", True, "2025-01-10T00:00:00Z"),
    "deploy-418.json": ("deploy", False, "2026-06-28T09:42:00Z"),
    "checkout-errors.log": ("log", False, "2026-06-28T09:48:00Z"),
    "payment-gateway-baseline.md": ("note", False, "2026-06-28T09:40:00Z"),
}


@dataclass(frozen=True, slots=True)
class SeedResult:
    dataset: str
    seeded: int
    reused: int
    failed: int
    ready: bool


@dataclass(frozen=True, slots=True)
class ResetResult:
    incident_id: str
    observation_count: int
    candidate_count: int


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class DemoService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        memory: CogneeMemoryPort,
        fixtures_dir: Path,
        dataset: str,
    ) -> None:
        self._session = session
        self._memory = memory
        self._fixtures_dir = fixtures_dir
        self._dataset = dataset

    @staticmethod
    def fixture_data_id(filename: str) -> str:
        relative_path = f"demo/fixtures/{filename}"
        return str(uuid5(DEMO_NAMESPACE, relative_path))

    async def seed(self, *, force: bool = False) -> SeedResult:
        seeded = 0
        reused = 0
        failed = 0

        for filename, (kind, is_stale, source_date) in EVIDENCE_FIXTURES.items():
            fixture_path = self._fixtures_dir / filename
            content = fixture_path.read_bytes()
            content_hash = f"sha256:{hashlib.sha256(content).hexdigest()}"
            data_id = self.fixture_data_id(filename)
            evidence = await self._session.get(EvidenceItem, data_id)
            if (
                not force
                and evidence is not None
                and evidence.content_hash == content_hash
                and evidence.status == "ready"
            ):
                reused += 1
                continue

            if evidence is None:
                evidence = EvidenceItem(
                    data_id=data_id,
                    dataset=self._dataset,
                    name=filename,
                    kind=kind,
                    status="queued",
                    content_hash=content_hash,
                    source_date=_parse_timestamp(source_date),
                    is_stale=is_stale,
                )
                self._session.add(evidence)
            else:
                evidence.dataset = self._dataset
                evidence.name = filename
                evidence.kind = kind
                evidence.content_hash = content_hash
                evidence.source_date = _parse_timestamp(source_date)
                evidence.is_stale = is_stale
                evidence.status = "queued"

            evidence.status = "processing"
            await self._session.flush()
            try:
                receipt = await self._memory.remember_evidence(
                    EvidencePayload(
                        data_id=data_id,
                        name=filename,
                        content=content,
                        dataset=self._dataset,
                    ),
                )
            except Exception:
                evidence.status = "failed"
                failed += 1
                continue

            if receipt.status not in {"completed", "running"}:
                evidence.status = "failed"
                failed += 1
                continue
            evidence.status = "ready"
            seeded += 1

        await self._session.commit()
        return SeedResult(
            dataset=self._dataset,
            seeded=seeded,
            reused=reused,
            failed=failed,
            ready=failed == 0,
        )

    async def reset(self) -> ResetResult:
        timeline = json.loads(
            (self._fixtures_dir / "incident-2048-timeline.json").read_text(
                encoding="utf-8",
            ),
        )
        incident_payload = timeline["incident"]
        existing = await self._session.get(Incident, incident_payload["id"])
        if existing is not None:
            await self._session.delete(existing)
            await self._session.flush()

        incident = Incident(
            id=incident_payload["id"],
            title=incident_payload["title"],
            severity=incident_payload["severity"],
            service=incident_payload["service"],
            status=incident_payload["status"],
            session_id=incident_payload["session_id"],
            started_at=_parse_timestamp(incident_payload["started_at"]),
        )
        self._session.add(incident)
        for observation_payload in timeline["observations"]:
            self._session.add(
                Observation(
                    id=observation_payload["id"],
                    incident_id=incident.id,
                    timestamp=_parse_timestamp(observation_payload["timestamp"]),
                    source=observation_payload["source"],
                    content=observation_payload["content"],
                    memory_status="pending",
                ),
            )
        for candidate_payload in timeline["memory_candidates"]:
            self._session.add(
                MemoryCandidate(
                    id=candidate_payload["id"],
                    incident_id=incident.id,
                    content=candidate_payload["content"],
                    state=candidate_payload["state"],
                ),
            )

        await self._session.commit()
        return ResetResult(
            incident_id=incident.id,
            observation_count=len(timeline["observations"]),
            candidate_count=len(timeline["memory_candidates"]),
        )
