import json
import os
from typing import Any

import faiss
import numpy as np

from infrastructure.embeddings import get_embedding

dimension = 384  # MiniLM embedding size
store_dir = os.path.join("data", ".vector_store")
index_path = os.path.join(store_dir, "index.faiss")
documents_path = os.path.join(store_dir, "documents.json")
metadata_path = os.path.join(store_dir, "metadata.json")

index = faiss.IndexFlatL2(dimension)
documents: list[str] = []
metadatas: list[dict[str, Any]] = []


def _ensure_store_dir() -> None:
    os.makedirs(store_dir, exist_ok=True)


def _load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_store() -> None:
    global index, documents, metadatas
    _ensure_store_dir()

    if os.path.exists(index_path):
        index = faiss.read_index(index_path)
    else:
        index = faiss.IndexFlatL2(dimension)

    documents = _load_json(documents_path, [])
    metadatas = _load_json(metadata_path, [])

    # Safety: keep metadata/doc arrays aligned.
    if len(documents) != len(metadatas):
        limit = min(len(documents), len(metadatas))
        documents = documents[:limit]
        metadatas = metadatas[:limit]


def save_store() -> None:
    _ensure_store_dir()
    faiss.write_index(index, index_path)
    with open(documents_path, "w", encoding="utf-8") as f:
        json.dump(documents, f, ensure_ascii=True, indent=2)
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadatas, f, ensure_ascii=True, indent=2)


def clear_store() -> None:
    global index, documents, metadatas
    index = faiss.IndexFlatL2(dimension)
    documents = []
    metadatas = []
    save_store()


def count_documents() -> int:
    return len(documents)


def get_all_metadata() -> list[dict[str, Any]]:
    return metadatas


def get_store_stats() -> dict[str, Any]:
    by_source_type: dict[str, int] = {}
    by_subject: dict[str, int] = {}
    by_year: dict[str, int] = {}

    for meta in metadatas:
        source_type = str(meta.get("source_type", "Unknown"))
        subject = str(meta.get("subject", "General"))
        year = meta.get("year")

        by_source_type[source_type] = by_source_type.get(source_type, 0) + 1
        by_subject[subject] = by_subject.get(subject, 0) + 1
        if year is not None:
            year_key = str(year)
            by_year[year_key] = by_year.get(year_key, 0) + 1

    def _sort_dict(d: dict[str, int]) -> dict[str, int]:
        return dict(sorted(d.items(), key=lambda item: item[1], reverse=True))

    return {
        "total_chunks": len(documents),
        "by_source_type": _sort_dict(by_source_type),
        "by_subject": _sort_dict(by_subject),
        "by_year": _sort_dict(by_year),
    }


def add_document(text: str, metadata: dict[str, Any] | None = None) -> None:
    vector = np.array([get_embedding(text)]).astype("float32")
    index.add(vector)
    documents.append(text)
    metadatas.append(metadata or {})


def search(query: str, k: int = 10) -> list[dict[str, Any]]:
    if not documents:
        return []

    top_k = min(k, len(documents))
    query_vector = np.array([get_embedding(query)]).astype("float32")
    distances, indices = index.search(query_vector, top_k)

    results = []
    for distance, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(documents):
            continue
        results.append(
            {
                "text": documents[idx],
                "metadata": metadatas[idx],
                "distance": float(distance),
                "index": int(idx),
            }
        )
    return results


load_store()
