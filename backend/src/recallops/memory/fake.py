from collections import defaultdict
from uuid import NAMESPACE_URL, uuid5

from recallops.memory.contract import (
    DatasetStatus,
    EvidencePayload,
    ForgetReceipt,
    ImproveReceipt,
    MemoryHealth,
    RecallEntry,
    RecallReference,
    RecallRequest,
    RememberReceipt,
)


class FakeMemoryError(RuntimeError):
    """Deterministic provider failure used by offline tests."""


class FakeCogneeAdapter:
    """In-memory implementation of the RecallOps memory contract."""

    def __init__(self, *, fail_operations: set[str] | None = None) -> None:
        self.evidence: dict[str, dict[str, EvidencePayload]] = defaultdict(dict)
        self.observations: dict[str, list[str]] = defaultdict(list)
        self.fail_operations = set(fail_operations or ())
        self.operation_counts: dict[str, int] = defaultdict(int)

    def _begin(self, operation: str) -> None:
        self.operation_counts[operation] += 1
        if operation in self.fail_operations:
            raise FakeMemoryError(f"configured fake {operation} failure")

    @staticmethod
    def _content_text(payload: EvidencePayload) -> str:
        if isinstance(payload.content, bytes):
            return payload.content.decode("utf-8", errors="replace")
        return payload.content

    @classmethod
    def _reference(cls, payload: EvidencePayload) -> RecallReference:
        return RecallReference(
            data_id=payload.data_id,
            chunk_id=str(uuid5(NAMESPACE_URL, f"{payload.data_id}:chunk:0")),
            document_name=payload.name,
            snippet=cls._content_text(payload)[:500],
        )

    async def remember_evidence(
        self,
        payload: EvidencePayload,
    ) -> RememberReceipt:
        self._begin("remember")
        self.evidence[payload.dataset][payload.data_id] = payload
        return RememberReceipt(status="completed", data_id=payload.data_id)

    async def remember_observation(
        self,
        session_id: str,
        content: str,
    ) -> RememberReceipt:
        self._begin("remember")
        self.observations[session_id].append(content)
        return RememberReceipt(status="completed")

    async def recall(self, request: RecallRequest) -> list[RecallEntry]:
        self._begin("recall")
        query = request.query.casefold()
        dataset = self.evidence.get(request.dataset, {})

        def references_for(*names: str) -> tuple[RecallReference, ...]:
            expected = set(names)
            return tuple(
                self._reference(payload)
                for payload in dataset.values()
                if payload.name in expected
            )

        if "verified mitigation" in query or "learn" in query:
            promoted = next(
                (
                    payload
                    for payload in dataset.values()
                    if payload.name == "verified-resolution-inc-2048.md"
                ),
                None,
            )
            if promoted is None:
                return []
            return [
                RecallEntry(
                    answer=self._content_text(promoted),
                    source="graph",
                    search_type="GRAPH_COMPLETION_CONTEXT_EXTENSION",
                    references=(self._reference(promoted),),
                ),
            ]

        golden_routes = (
            (
                "which previous incident resembles",
                (
                    "INC-1842 resembles the current checkout outage: both involved "
                    "Redis session TTL behavior after a deployment."
                ),
                ("postmortem-inc-1842.md",),
            ),
            (
                "connected to redis session misses",
                (
                    "deploy-418 changed the session TTL to milliseconds without the "
                    "required conversion, producing Redis session misses."
                ),
                ("deploy-418.json", "postmortem-inc-1842.md"),
            ),
            (
                "what changed immediately before latency",
                (
                    "deploy-418 changed SESSION_TTL_MS to milliseconds while the "
                    "adapter still required a seconds-to-milliseconds conversion."
                ),
                ("deploy-418.json",),
            ),
            (
                "root cause of inc-1842",
                (
                    "INC-1842 was caused by a missing seconds-to-milliseconds "
                    "conversion in Redis session TTL handling."
                ),
                ("postmortem-inc-1842.md",),
            ),
            (
                "which runbook instruction is now stale",
                (
                    "The instruction to flush all Redis cache is obsolete and was "
                    "superseded by checkout-runbook-v3."
                ),
                ("stale-cache-reset-rule.md",),
            ),
            (
                "contradicts payment-gateway rate limiting",
                (
                    "Payment gateway latency stayed at baseline and no rate limit "
                    "response aligned with the checkout errors."
                ),
                ("checkout-errors.log", "payment-gateway-baseline.md"),
            ),
            (
                "summarize the incident timeline",
                (
                    "deploy-418 was followed by checkout p95 above 4 seconds and a "
                    "640 percent increase in Redis session misses."
                ),
                ("deploy-418.json", "checkout-errors.log"),
            ),
            (
                "services depend on the affected redis path",
                (
                    "checkout-api depends on the Redis session path described by the "
                    "postmortem and checkout runbook."
                ),
                ("postmortem-inc-1842.md", "checkout-runbook-v3.md"),
            ),
            (
                "what mitigation was verified",
                (
                    "The verified mitigation was to roll back the TTL configuration "
                    "and reissue affected sessions."
                ),
                ("postmortem-inc-1842.md", "checkout-runbook-v3.md"),
            ),
        )
        for marker, answer, document_names in golden_routes:
            if marker in query:
                return [
                    RecallEntry(
                        answer=answer,
                        source="graph",
                        search_type="GRAPH_COMPLETION_CONTEXT_EXTENSION",
                        references=references_for(*document_names),
                    ),
                ]

        if any(term in query for term in ("deploy-418", "redis incident", "related")):
            relationship_evidence = references_for(
                "postmortem-inc-1842.md",
                "stale-cache-reset-rule.md",
            )
            return [
                RecallEntry(
                    answer=(
                        "INC-1842 is the closest prior incident because both outages "
                        "followed a checkout deployment that changed Redis session TTL "
                        "behavior."
                    ),
                    source="graph",
                    search_type="GRAPH_COMPLETION_CONTEXT_EXTENSION",
                    references=relationship_evidence,
                ),
            ]

        matching = tuple(
            self._reference(payload)
            for payload in dataset.values()
            if any(
                term in self._content_text(payload).casefold()
                for raw_term in query.split()
                if (
                    term := raw_term.strip("\"'.,:;!?()[]{}")
                )
                if len(term) > 3
            )
        )
        if not matching:
            return []
        return [
            RecallEntry(
                answer="Relevant evidence was found in permanent memory.",
                source="graph",
                search_type="CHUNKS",
                references=matching,
            ),
        ]

    async def improve_session(
        self,
        dataset: str,
        session_ids: list[str],
    ) -> ImproveReceipt:
        self._begin("improve")
        for session_id in session_ids:
            resolution = next(
                (
                    observation
                    for observation in reversed(self.observations.get(session_id, []))
                    if "verified resolution" in observation.casefold()
                ),
                None,
            )
            if resolution is None:
                continue
            data_id = str(uuid5(NAMESPACE_URL, f"{dataset}:{session_id}:resolution"))
            self.evidence[dataset][data_id] = EvidencePayload(
                data_id=data_id,
                name="verified-resolution-inc-2048.md",
                content=resolution,
                dataset=dataset,
            )
        return ImproveReceipt(
            status="completed",
            session_ids=tuple(session_ids),
        )

    async def forget_evidence_item(
        self,
        dataset: str,
        data_id: str,
    ) -> ForgetReceipt:
        self._begin("forget")
        removed = self.evidence.get(dataset, {}).pop(data_id, None)
        return ForgetReceipt(
            status="deleted" if removed is not None else "not_found",
            data_id=data_id,
        )

    async def dataset_status(self, dataset: str) -> DatasetStatus:
        self._begin("dataset_status")
        return DatasetStatus(dataset=dataset, ready=True, status="ready")

    async def health(self) -> MemoryHealth:
        self._begin("health")
        return MemoryHealth(reachable=True, mode="fake")
