import json
from pathlib import Path

import pytest

from recallops.memory.normalize import RecallContractError, normalize_recall

FIXTURE = Path(__file__).parents[1] / "fixtures" / "cognee" / "graph-recall.json"


def test_normalizes_recorded_verbose_graph_response() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))

    entries = normalize_recall(raw)

    assert entries[0].source == "graph"
    assert entries[0].search_type == "GRAPH_COMPLETION_CONTEXT_EXTENSION"
    assert entries[0].references[0].data_id == ("11111111-1111-4111-8111-111111111111")
    assert entries[0].references[0].chunk_id == ("22222222-2222-4222-8222-222222222222")
    assert entries[0].references[0].document_name == ("cloudflare-november-18-postmortem.md")


def test_normalizes_plain_string_response() -> None:
    entries = normalize_recall("A prior global-configuration incident was found.")

    assert entries[0].answer == ("A prior global-configuration incident was found.")
    assert entries[0].source == "graph"
    assert entries[0].search_type == "unknown"
    assert entries[0].references == ()
    assert entries[0].raw_kind == "string"


def test_normalizes_a_list_with_multiple_supported_shapes() -> None:
    entries = normalize_recall(
        [
            "First result",
            {
                "result": "Second result",
                "source": "session",
                "searchType": "CHUNKS",
            },
        ],
    )

    assert [entry.answer for entry in entries] == ["First result", "Second result"]
    assert entries[1].source == "session"
    assert entries[1].references == ()


def test_normalizes_alternate_reference_key_names() -> None:
    entries = normalize_recall(
        {
            "answer": "Referenced result",
            "references": [
                {
                    "dataId": "data-1",
                    "chunkId": "chunk-1",
                    "documentName": "runbook.md",
                    "text": "Rollback the global configuration.",
                },
            ],
        },
    )

    reference = entries[0].references[0]
    assert reference.data_id == "data-1"
    assert reference.chunk_id == "chunk-1"
    assert reference.document_name == "runbook.md"
    assert reference.snippet == "Rollback the global configuration."


def test_normalizes_cognee_1_2_search_result_item_with_evidence_block() -> None:
    entries = normalize_recall(
        {
            "kind": "graph_completion",
            "search_type": "GRAPH_COMPLETION_CONTEXT_EXTENSION",
            "text": (
                "The contract marker is amber-orbit-731.\n\n"
                "Evidence:\n"
                "- chunk 1 of document recallops-live-contract.txt "
                "(data_id: d1d38b21-e5e8-59d3-aa7f-613a16fa960d, "
                "chunk_id: 22222222-2222-4222-8222-222222222222): "
                '"RecallOps contract marker 2026-06-28: amber-orbit-731."'
            ),
            "metadata": {},
            "raw": {},
        },
    )

    assert entries[0].answer == "The contract marker is amber-orbit-731."
    assert entries[0].search_type == "GRAPH_COMPLETION_CONTEXT_EXTENSION"
    assert entries[0].references[0].document_name == "recallops-live-contract.txt"
    assert entries[0].references[0].data_id == ("d1d38b21-e5e8-59d3-aa7f-613a16fa960d")
    assert entries[0].references[0].chunk_id == ("22222222-2222-4222-8222-222222222222")


def test_rejects_unsupported_recall_rows() -> None:
    with pytest.raises(RecallContractError, match="unsupported recall row: int"):
        normalize_recall(42)
