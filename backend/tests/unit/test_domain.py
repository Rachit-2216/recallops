import pytest

from recallops.domain.enums import MemoryCandidateState
from recallops.domain.models import IncidentRecord, InvalidTransition


def test_incident_can_only_resolve_with_complete_resolution() -> None:
    incident = IncidentRecord.active_demo()
    with pytest.raises(InvalidTransition, match="root cause"):
        incident.resolve(
            root_cause="",
            mitigation="Rolled back TTL configuration.",
            verification="Checkout p95 recovered.",
            reference_count=2,
        )


def test_verified_candidate_can_be_promoted() -> None:
    assert MemoryCandidateState.VERIFIED.can_transition_to(
        MemoryCandidateState.PROMOTED,
    )


def test_rejected_session_hypothesis_cannot_be_marked_forgotten() -> None:
    assert not MemoryCandidateState.REJECTED.can_transition_to(
        MemoryCandidateState.FORGOTTEN,
    )
