from dataclasses import dataclass

DEFAULT_ESTIMATES = {
    "remember": 250_000,
    "recall": 20_000,
    "improve": 300_000,
    "forget": 10_000,
}


class CreditBudgetExceeded(RuntimeError):
    """Raised when an operation would enter the protected credit reserve."""


@dataclass(frozen=True, slots=True)
class CreditDecision:
    allowed: bool
    reason: str
    remaining_before: int
    remaining_after: int


class CreditGuard:
    def __init__(self, *, supply: int, protected_reserve: int) -> None:
        if supply <= 0:
            raise ValueError("token supply must be positive")
        if protected_reserve < 0:
            raise ValueError("protected reserve must be non-negative")
        if protected_reserve >= supply:
            raise ValueError("protected reserve must be smaller than token supply")
        self.supply = supply
        self.protected_reserve = protected_reserve
        self.estimated_used = 0

    @staticmethod
    def _validate(operation: str, estimated_tokens: int) -> None:
        if operation not in DEFAULT_ESTIMATES:
            raise ValueError(f"unknown memory operation: {operation}")
        if estimated_tokens < 0:
            raise ValueError("estimated tokens must be non-negative")

    def record_estimate(self, operation: str, estimated_tokens: int) -> None:
        self._validate(operation, estimated_tokens)
        self.estimated_used += estimated_tokens

    def authorize(
        self,
        operation: str,
        *,
        estimated_tokens: int | None = None,
        essential: bool,
    ) -> CreditDecision:
        estimate = (
            DEFAULT_ESTIMATES[operation]
            if estimated_tokens is None and operation in DEFAULT_ESTIMATES
            else estimated_tokens
        )
        if estimate is None:
            raise ValueError(f"unknown memory operation: {operation}")
        self._validate(operation, estimate)

        remaining_before = self.supply - self.estimated_used
        remaining_after = remaining_before - estimate
        if remaining_after < self.protected_reserve:
            category = "essential" if essential else "nonessential"
            raise CreditBudgetExceeded(
                f"{category} {operation} would enter the protected reserve",
            )
        return CreditDecision(
            allowed=True,
            reason="operation remains above protected reserve",
            remaining_before=remaining_before,
            remaining_after=remaining_after,
        )
