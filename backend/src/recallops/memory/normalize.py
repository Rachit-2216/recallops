import re

from recallops.memory.contract import RecallEntry, RecallReference


class RecallContractError(ValueError):
    """Raised when a provider recall payload cannot be normalized safely."""


EVIDENCE_MARKER = "\nEvidence:\n"
EVIDENCE_REFERENCE_PATTERN = re.compile(
    r"^- chunk \d+ of document (?P<document_name>.+?) "
    r"\(data_id: (?P<data_id>[^,]+), chunk_id: (?P<chunk_id>[^)]+)\): "
    r'"(?P<snippet>.*)"$',
)


def _optional_text(
    value: dict[object, object],
    *keys: str,
) -> str | None:
    for key in keys:
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


def _required_text(
    value: dict[object, object],
    label: str,
    *keys: str,
) -> str:
    result = _optional_text(value, *keys)
    if result is None:
        raise RecallContractError(f"recall reference is missing {label}")
    return result


def _normalize_reference(raw: object) -> RecallReference:
    if not isinstance(raw, dict):
        raise RecallContractError(
            f"unsupported recall reference: {type(raw).__name__}",
        )
    return RecallReference(
        data_id=_required_text(raw, "data_id", "data_id", "dataId"),
        chunk_id=_required_text(raw, "chunk_id", "chunk_id", "chunkId"),
        document_name=_required_text(
            raw,
            "document_name",
            "document_name",
            "documentName",
            "file_name",
            "name",
        ),
        snippet=_required_text(raw, "snippet", "snippet", "text", "content"),
    )


def _split_evidence(answer: str) -> tuple[str, tuple[RecallReference, ...]]:
    if EVIDENCE_MARKER not in answer:
        return answer, ()
    answer_text, evidence = answer.split(EVIDENCE_MARKER, maxsplit=1)
    references = []
    for line in evidence.splitlines():
        match = EVIDENCE_REFERENCE_PATTERN.fullmatch(line)
        if match is None:
            continue
        references.append(
            RecallReference(
                data_id=match.group("data_id").strip(),
                chunk_id=match.group("chunk_id").strip(),
                document_name=match.group("document_name").strip(),
                snippet=match.group("snippet").strip(),
            ),
        )
    return answer_text.strip(), tuple(references)


def normalize_recall_dict(row: dict[object, object]) -> RecallEntry:
    raw_answer = _optional_text(row, "answer", "result", "content", "text")
    if raw_answer is None:
        raise RecallContractError("recall row is missing a string answer")
    answer, embedded_references = _split_evidence(raw_answer)

    raw_references = row.get("references", ())
    if raw_references is None:
        references = embedded_references
    elif raw_references == ():
        references = embedded_references
    elif isinstance(raw_references, dict):
        references = (_normalize_reference(raw_references),)
    elif isinstance(raw_references, list | tuple):
        references = tuple(_normalize_reference(item) for item in raw_references)
    else:
        raise RecallContractError(
            "recall references must be a list, tuple, dictionary, or null",
        )

    return RecallEntry(
        answer=answer,
        source=_optional_text(row, "_source", "source") or "graph",
        search_type=_optional_text(row, "search_type", "searchType") or "unknown",
        references=references,
        raw_kind="dictionary",
    )


def normalize_recall(raw: object) -> list[RecallEntry]:
    rows = raw if isinstance(raw, list) else [raw]
    entries: list[RecallEntry] = []
    for row in rows:
        if isinstance(row, str):
            entries.append(
                RecallEntry(
                    answer=row,
                    source="graph",
                    search_type="unknown",
                    references=(),
                    raw_kind="string",
                ),
            )
            continue
        if not isinstance(row, dict):
            raise RecallContractError(
                f"unsupported recall row: {type(row).__name__}",
            )
        entries.append(normalize_recall_dict(row))
    return entries
