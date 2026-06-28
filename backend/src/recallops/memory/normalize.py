from recallops.memory.contract import RecallEntry, RecallReference


class RecallContractError(ValueError):
    """Raised when a provider recall payload cannot be normalized safely."""


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


def normalize_recall_dict(row: dict[object, object]) -> RecallEntry:
    answer = _optional_text(row, "answer", "result", "content")
    if answer is None:
        raise RecallContractError("recall row is missing a string answer")

    raw_references = row.get("references", ())
    if raw_references is None:
        references: tuple[RecallReference, ...] = ()
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
