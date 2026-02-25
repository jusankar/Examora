from typing import Any

from infrastructure.vector_store import search

SOURCE_WEIGHTS = {
    "TextBooks": 1.35,
    "PYQ": 1.2,
    "SQP": 1.05,
    "MarkingScheme": 1.1,
    "Curriculum": 1.05,
}


def _passes_filters(metadata: dict[str, Any], filters: dict[str, Any]) -> bool:
    subject = filters.get("subject")
    if subject and str(metadata.get("subject", "")).lower() != str(subject).lower():
        return False

    source_types = filters.get("source_types")
    if source_types:
        allowed = {str(item).lower() for item in source_types}
        if str(metadata.get("source_type", "")).lower() not in allowed:
            return False

    year_from = filters.get("year_from")
    year_to = filters.get("year_to")
    year = metadata.get("year")
    if year is not None:
        if year_from is not None and year < int(year_from):
            return False
        if year_to is not None and year > int(year_to):
            return False

    return True


def retrieve_context(query: str, top_k: int = 6, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    filters = filters or {}
    raw = search(query, k=max(top_k * 4, 12))
    scored = []

    for item in raw:
        metadata = item.get("metadata", {})
        if not _passes_filters(metadata, filters):
            continue

        source_type = metadata.get("source_type", "Unknown")
        weight = SOURCE_WEIGHTS.get(source_type, 1.0)
        distance = float(item.get("distance", 0.0))
        score = weight / (1.0 + distance)

        scored.append({**item, "score": score})

    scored.sort(key=lambda row: row["score"], reverse=True)
    return scored[:top_k]
