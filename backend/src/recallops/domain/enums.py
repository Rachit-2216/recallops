from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType


class IncidentSeverity(StrEnum):
    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"


class IncidentStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"


class EvidenceKind(StrEnum):
    RUNBOOK = "runbook"
    POSTMORTEM = "postmortem"
    DEPLOY = "deploy"
    LOG = "log"
    NOTE = "note"
    URL = "url"
    MEMORY_CANDIDATE = "memory_candidate"


class EvidenceStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    FORGOTTEN = "forgotten"


class ObservationSource(StrEnum):
    HUMAN = "human"
    SYSTEM = "system"
    RECALLOPS = "recallops"


class MemoryCandidateState(StrEnum):
    PROPOSED = "proposed"
    PINNED = "pinned"
    VERIFIED = "verified"
    PROMOTED = "promoted"
    REJECTED = "rejected"
    FORGOTTEN = "forgotten"
    SUPERSEDED = "superseded"

    def can_transition_to(self, target: "MemoryCandidateState") -> bool:
        return target in MEMORY_CANDIDATE_TRANSITIONS[self]


class VerificationState(StrEnum):
    REFERENCED = "referenced"
    UNVERIFIED = "unverified"
    CONTRADICTED = "contradicted"


class PromotionState(StrEnum):
    NOT_REQUESTED = "not_requested"
    PROMOTION_PENDING = "promotion_pending"
    PROMOTED = "promoted"
    PROMOTION_FAILED = "promotion_failed"


MEMORY_CANDIDATE_TRANSITIONS: Mapping[
    MemoryCandidateState,
    frozenset[MemoryCandidateState],
] = MappingProxyType(
    {
        MemoryCandidateState.PROPOSED: frozenset(
            {
                MemoryCandidateState.PINNED,
                MemoryCandidateState.REJECTED,
            },
        ),
        MemoryCandidateState.PINNED: frozenset(
            {
                MemoryCandidateState.VERIFIED,
                MemoryCandidateState.FORGOTTEN,
            },
        ),
        MemoryCandidateState.VERIFIED: frozenset(
            {
                MemoryCandidateState.PROMOTED,
                MemoryCandidateState.SUPERSEDED,
            },
        ),
        MemoryCandidateState.PROMOTED: frozenset(
            {
                MemoryCandidateState.SUPERSEDED,
            },
        ),
        MemoryCandidateState.REJECTED: frozenset(),
        MemoryCandidateState.FORGOTTEN: frozenset(),
        MemoryCandidateState.SUPERSEDED: frozenset(),
    },
)
