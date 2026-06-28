import pytest

from recallops.services.credit_guard import (
    CreditBudgetExceeded,
    CreditGuard,
)


def test_heavy_operation_is_blocked_at_reserve_boundary() -> None:
    guard = CreditGuard(supply=14_000_000, protected_reserve=6_000_000)
    guard.record_estimate("remember", 7_800_000)

    with pytest.raises(CreditBudgetExceeded):
        guard.authorize("improve", estimated_tokens=300_000, essential=False)


def test_final_demo_operation_can_use_rehearsal_allowance_not_reserve() -> None:
    guard = CreditGuard(supply=14_000_000, protected_reserve=6_000_000)
    guard.record_estimate("remember", 7_000_000)

    decision = guard.authorize(
        "recall",
        estimated_tokens=10_000,
        essential=True,
    )

    assert decision.allowed is True
    assert decision.remaining_after == 6_990_000


@pytest.mark.parametrize("estimate", [-1, -50_000])
def test_negative_estimates_are_rejected(estimate: int) -> None:
    guard = CreditGuard(supply=14_000_000, protected_reserve=6_000_000)

    with pytest.raises(ValueError, match="non-negative"):
        guard.authorize("recall", estimated_tokens=estimate, essential=False)


def test_unknown_operations_are_rejected() -> None:
    guard = CreditGuard(supply=14_000_000, protected_reserve=6_000_000)

    with pytest.raises(ValueError, match="unknown memory operation"):
        guard.authorize("rebuild_everything", estimated_tokens=1, essential=False)
