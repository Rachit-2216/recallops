import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from recallops.memory.contract import EvidencePayload, RecallRequest
from recallops.memory.fake import FakeCogneeAdapter
from recallops.services.demo import EVIDENCE_FIXTURES, DemoService

ROOT = Path(__file__).resolve().parents[1]
DATASET = "recallops_evidence_v1"
FIXTURES = ROOT / "demo" / "fixtures"
EXPECTED = FIXTURES / "expected-retrieval.json"
REPORT = ROOT / "outputs" / "evaluation-report.json"


async def evaluate_fake() -> tuple[dict[str, int], list[dict[str, Any]]]:
    memory = FakeCogneeAdapter()
    for filename in EVIDENCE_FIXTURES:
        await memory.remember_evidence(
            EvidencePayload(
                data_id=DemoService.fixture_data_id(filename),
                name=filename,
                content=(FIXTURES / filename).read_bytes(),
                dataset=DATASET,
            ),
        )

    resolution = (
        "Verified resolution for INC-2048: Root cause: TTL configuration used "
        "milliseconds with a seconds-based adapter. Mitigation: rolled back the "
        "TTL configuration and reissued affected sessions. Verification: checkout "
        "latency and Redis session misses returned to baseline."
    )
    await memory.remember_observation("incident:INC-2048", resolution)
    await memory.improve_session(DATASET, ["incident:INC-2048"])

    cases = json.loads(EXPECTED.read_text(encoding="utf-8"))
    scores = {
        "document_recall": 0,
        "required_concepts": 0,
        "forbidden_claims": 0,
        "reference_parsing": 0,
    }
    results: list[dict[str, Any]] = []
    for case in cases:
        entries = await memory.recall(
            RecallRequest(
                query=case["question"],
                dataset=DATASET,
                session_id="incident:evaluation",
            ),
        )
        answer = " ".join(entry.answer for entry in entries)
        references = [
            reference
            for entry in entries
            for reference in entry.references
        ]
        documents = {reference.document_name for reference in references}
        document_ok = set(case["expected_documents"]) <= documents
        concepts_ok = all(
            concept.casefold() in answer.casefold()
            for concept in case["required_concepts"]
        )
        forbidden_ok = all(
            claim.casefold() not in answer.casefold()
            for claim in case["forbidden_claims"]
        )
        references_ok = bool(references) and all(
            reference.data_id
            and reference.chunk_id
            and reference.document_name
            and reference.snippet
            for reference in references
        )
        scores["document_recall"] += int(document_ok)
        scores["required_concepts"] += int(concepts_ok)
        scores["forbidden_claims"] += int(forbidden_ok)
        scores["reference_parsing"] += int(references_ok)
        results.append(
            {
                "question": case["question"],
                "documents": sorted(documents),
                "document_recall": document_ok,
                "required_concepts": concepts_ok,
                "forbidden_claims": forbidden_ok,
                "reference_parsing": references_ok,
            },
        )
    return scores, results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", choices=["fake"], default="fake")
    return parser.parse_args()


def main() -> int:
    parse_args()
    scores, results = asyncio.run(evaluate_fake())
    total = len(results)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        json.dumps(
            {"adapter": "fake", "total": total, "scores": scores, "cases": results},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    labels = {
        "document_recall": "document recall",
        "required_concepts": "required concepts",
        "forbidden_claims": "forbidden claims",
        "reference_parsing": "reference parsing",
    }
    for metric, label in labels.items():
        print(f"{label}: {scores[metric]}/{total}")
    return 0 if all(score == total for score in scores.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
