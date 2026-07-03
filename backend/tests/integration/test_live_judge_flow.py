import hashlib
import json
import os
from pathlib import Path
from time import monotonic
from typing import Any

import pytest

from recallops.config import Settings
from recallops.memory.cognee_cloud import CogneeCloudAdapter
from recallops.memory.contract import EvidencePayload, RecallEntry, RecallRequest
from recallops.services.demo import DemoService

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_COGNEE_INTEGRATION") != "1"
        or os.getenv("COGNEE_DASHBOARD_CONFIRMED") != "1",
        reason="live lifecycle requires opt-in and a confirmed credit dashboard",
    ),
]

ROOT = Path(__file__).parents[3]
FIXTURES = ROOT / "demo" / "fixtures"
REPORT = ROOT / "outputs" / "live-lifecycle-report.json"
DATASET = "recallops_evidence_v1"
INCIDENT_ID = "CF-OUTAGE-2025-12-05"
SESSION = f"incident:{INCIDENT_ID}"
PROOF_SESSION = f"incident:{INCIDENT_ID}-proof"
RELATIONSHIP_QUERY = "How is the December 5 outage related to the November 18 outage?"
STALE_QUERY = '"Any WAF rule can be disabled through the global configuration killswitch"'
FIXTURE_PROBES = {
    "cloudflare-december-5-postmortem.md": "December 5 FL1 execute nil",
    "cloudflare-november-18-postmortem.md": ("November 18 Bot Management feature file"),
    "code-orange-fail-small-guidance.md": "controlled rollout health rollback",
    "unsafe-global-killswitch-assumption.md": STALE_QUERY,
    "cloudflare-december-5-change.json": "global WAF configuration killswitch",
    "cloudflare-december-5-derived-events.log": ("08:47 09:11 09:12 traffic restored"),
}


def _documents(entries: list[RecallEntry]) -> list[str]:
    return sorted(
        {reference.document_name for entry in entries for reference in entry.references},
    )


@pytest.mark.asyncio
async def test_one_controlled_live_judge_lifecycle() -> None:
    settings = Settings(_env_file=None)
    assert settings.cognee_base_url is not None
    assert settings.cognee_api_key is not None
    memory = CogneeCloudAdapter(
        base_url=settings.cognee_base_url,
        api_key=settings.cognee_api_key.get_secret_value(),
    )
    report: dict[str, Any] = {
        "dataset": DATASET,
        "fixtures": [],
        "operations": [],
        "assertions": {},
    }

    for filename, probe in FIXTURE_PROBES.items():
        content = (FIXTURES / filename).read_bytes()
        data_id = DemoService.fixture_data_id(filename)
        content_hash = hashlib.sha256(content).hexdigest()
        started = monotonic()
        existing = await memory.recall(
            RecallRequest(
                query=probe,
                dataset=DATASET,
                session_id=SESSION,
            ),
        )
        exists = any(
            reference.data_id == data_id and reference.document_name == filename
            for entry in existing
            for reference in entry.references
        )
        status = "existing"
        if not exists:
            receipt = await memory.remember_evidence(
                EvidencePayload(
                    data_id=data_id,
                    name=filename,
                    content=content,
                    dataset=DATASET,
                ),
            )
            assert receipt.status in {"completed", "running"}
            status = "seeded_missing"
        report["fixtures"].append(
            {
                "document": filename,
                "data_id": data_id,
                "hash_prefix": content_hash[:12],
                "status": status,
                "duration_ms": round((monotonic() - started) * 1000, 2),
            },
        )

    timeline = json.loads(
        (FIXTURES / "cloudflare-december-5-timeline.json").read_text(
            encoding="utf-8",
        ),
    )
    started = monotonic()
    for observation in timeline["observations"]:
        receipt = await memory.remember_observation(
            SESSION,
            observation["content"],
        )
        assert receipt.status in {"completed", "session_stored"}
    report["operations"].append(
        {
            "operation": "remember_observations",
            "status": "completed",
            "count": 3,
            "duration_ms": round((monotonic() - started) * 1000, 2),
        },
    )

    started = monotonic()
    recalled = await memory.recall(
        RecallRequest(
            query=RELATIONSHIP_QUERY,
            dataset=DATASET,
            session_id=SESSION,
        ),
    )
    relationship_documents = _documents(recalled)
    assert "cloudflare-november-18-postmortem.md" in relationship_documents
    report["operations"].append(
        {
            "operation": "relationship_recall",
            "status": "referenced",
            "documents": relationship_documents,
            "duration_ms": round((monotonic() - started) * 1000, 2),
        },
    )

    stale_name = "unsafe-global-killswitch-assumption.md"
    stale_id = DemoService.fixture_data_id(stale_name)
    started = monotonic()
    forgotten = await memory.forget_evidence_item(DATASET, stale_id)
    assert forgotten.status in {"deleted", "not_found"}
    after_forget = await memory.recall(
        RecallRequest(
            query=STALE_QUERY,
            dataset=DATASET,
            session_id=SESSION,
        ),
    )
    after_documents = _documents(after_forget)
    assert stale_name not in after_documents
    report["operations"].append(
        {
            "operation": "forget_one",
            "status": forgotten.status,
            "document": stale_name,
            "verified_absent": True,
            "duration_ms": round((monotonic() - started) * 1000, 2),
        },
    )

    resolution = (
        f"Verified resolution for {INCIDENT_ID}: Root cause: a global killswitch "
        "exposed nil handling in FL1. Mitigation: used a controlled rollout and "
        "rollback. Verification: traffic was restored by 09:12 UTC."
    )
    started = monotonic()
    remembered = await memory.remember_observation(SESSION, resolution)
    assert remembered.status in {"completed", "session_stored"}
    improved = await memory.improve_session(DATASET, [SESSION])
    assert improved.status == "completed"
    report["operations"].append(
        {
            "operation": "improve",
            "status": improved.status,
            "session_count": len(improved.session_ids),
            "duration_ms": round((monotonic() - started) * 1000, 2),
        },
    )

    started = monotonic()
    proof = await memory.recall(
        RecallRequest(
            query=f"What verified mitigation fixed {INCIDENT_ID}?",
            dataset=DATASET,
            session_id=PROOF_SESSION,
        ),
    )
    proof_documents = _documents(proof)
    proof_text = " ".join(entry.answer for entry in proof)
    assert "controlled rollout" in proof_text.casefold()
    assert proof_documents
    report["operations"].append(
        {
            "operation": "clean_session_recall",
            "status": "referenced",
            "documents": proof_documents,
            "duration_ms": round((monotonic() - started) * 1000, 2),
        },
    )
    report["assertions"] = {
        "relationship_referenced": True,
        "stale_item_absent": True,
        "improve_called_once": True,
        "clean_session_resolution_found": True,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
