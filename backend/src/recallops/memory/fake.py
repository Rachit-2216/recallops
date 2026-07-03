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
                self._reference(payload) for payload in dataset.values() if payload.name in expected
            )

        if "verified mitigation" in query or "learn" in query:
            promoted = next(
                (
                    payload
                    for payload in dataset.values()
                    if payload.name == "verified-resolution-cf-outage-2025-12-05.md"
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
                "which previous outage most closely resembles",
                (
                    "The November 18 outage most closely resembles the December 5 "
                    "incident because both exposed the blast-radius risk of rapid "
                    "global configuration propagation."
                ),
                ("cloudflare-november-18-postmortem.md",),
            ),
            (
                "how did the december 5 waf configuration change",
                (
                    "The global killswitch removed the execute field from an FL1 "
                    "rules object; Lua code then dereferenced the resulting nil "
                    "value and returned HTTP 500 errors."
                ),
                (
                    "cloudflare-december-5-change.json",
                    "cloudflare-december-5-postmortem.md",
                ),
            ),
            (
                "how much traffic was affected",
                (
                    "Approximately 28 percent of Cloudflare HTTP traffic was "
                    "affected for about 25 minutes."
                ),
                (
                    "cloudflare-december-5-postmortem.md",
                    "cloudflare-december-5-derived-events.log",
                ),
            ),
            (
                "root cause of the november 18 outage",
                (
                    "A database permissions change caused duplicate rows in the "
                    "Bot Management feature file, which doubled before global "
                    "propagation."
                ),
                ("cloudflare-november-18-postmortem.md",),
            ),
            (
                "which assumption about global killswitches is unsafe",
                (
                    "It is unsafe to assume a global killswitch can remove execute "
                    "without validation or a gradual rollout."
                ),
                ("unsafe-global-killswitch-assumption.md",),
            ),
            (
                "contradicts the cyber-attack hypothesis",
                (
                    "Cloudflare's postmortem attributes the failure to its own "
                    "configuration change, not a cyber attack."
                ),
                ("cloudflare-december-5-postmortem.md",),
            ),
            (
                "sequence restored traffic",
                (
                    "Operators reverted the configuration at 09:11 UTC, and "
                    "traffic was restored by 09:12 UTC."
                ),
                (
                    "cloudflare-december-5-derived-events.log",
                    "cloudflare-december-5-postmortem.md",
                ),
            ),
            (
                "what rollout controls does code orange recommend",
                (
                    "Code Orange recommends controlled rollout stages with health "
                    "gates and automatic rollback when signals regress."
                ),
                ("code-orange-fail-small-guidance.md",),
            ),
            (
                "how should invalid configuration fail safely",
                (
                    "Invalid configuration should preserve a known-good state or "
                    "take a safe path that continues serving traffic."
                ),
                ("code-orange-fail-small-guidance.md",),
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

        if any(term in query for term in ("december 5", "november 18", "related")):
            relationship_evidence = references_for(
                "cloudflare-november-18-postmortem.md",
                "unsafe-global-killswitch-assumption.md",
            )
            return [
                RecallEntry(
                    answer=(
                        "November 18 is the closest prior incident because both "
                        "outages exposed the blast-radius risk of rapid global "
                        "configuration propagation."
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
                if (term := raw_term.strip("\"'.,:;!?()[]{}"))
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
            incident_id = session_id.removeprefix("incident:").lower()
            self.evidence[dataset][data_id] = EvidencePayload(
                data_id=data_id,
                name=f"verified-resolution-{incident_id}.md",
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
