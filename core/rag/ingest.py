import os
import re
from typing import Any

import pdfplumber

from infrastructure.vector_store import add_document, clear_store, count_documents, save_store

SUPPORTED_EXTENSIONS = {".pdf"}


def split_text(text: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []

    chunks = []
    start = 0
    while start < len(cleaned):
        end = start + chunk_size
        chunks.append(cleaned[start:end])
        start = max(end - overlap, start + 1)
    return chunks


def _normalize_folder_name(name: str) -> str:
    lowered = name.strip().lower().replace(" ", "")
    mapping = {
        "textbooks": "TextBooks",
        "textbook": "TextBooks",
        "pyq": "PYQ",
        "sqp": "SQP",
        "markingscheme": "MarkingScheme",
        "readingmaterials": "Curriculum",
        "curriculum": "Curriculum",
        "syllabus": "Curriculum",
    }
    return mapping.get(lowered, name)


def _tokenize_name(value: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", value.lower()) if token}


def _infer_source_type(parts: list[str], file_name: str) -> str:
    if not parts:
        return "Unknown"

    first_folder = _normalize_folder_name(parts[0])
    canonical = {"TextBooks", "PYQ", "SQP", "MarkingScheme", "Curriculum"}
    if first_folder in canonical:
        return first_folder

    joined = " ".join(parts + [file_name]).lower()
    tokens = _tokenize_name(joined)

    if (
        {"textbook", "textbooks", "ncert"} & tokens
        or "text book" in joined
        or re.search(r"\btb\b", joined)
    ):
        return "TextBooks"
    if (
        {"pyq", "previous", "year", "board"} <= tokens
        or {"previous", "year"} <= tokens
        or "previous year" in joined
    ):
        return "PYQ"
    if (
        {"sqp", "sample", "model"} & tokens
        or "sample paper" in joined
        or "model paper" in joined
    ):
        return "SQP"
    if (
        {"marking", "scheme", "answers", "rubric", "ms"} & tokens
        or "marking scheme" in joined
        or re.search(r"\bms\b", joined)
    ):
        return "MarkingScheme"
    if (
        {"curriculum", "syllabus", "blueprint", "weightage", "readingmaterials", "rm"} & tokens
        or "reading material" in joined
    ):
        return "Curriculum"

    return first_folder


def _extract_year(parts: list[str], file_name: str) -> int | None:
    for value in [*parts, file_name]:
        match = re.search(r"(20\d{2})", value)
        if match:
            return int(match.group(1))
    return None


def _normalize_subject(value: str) -> str:
    key = value.strip().lower().replace(" ", "").replace("_", "").replace("-", "")
    mapping = {
        "science": "Science",
        "socialscience": "SocialScience",
        "ss": "SocialScience",
        "sst": "SocialScience",
        "socialstudies": "SocialScience",
        "mathematics": "Mathematics",
        "maths": "Mathematics",
        "math": "Mathematics",
        "mathsbasic": "MathematicsBasic",
        "mathsstandard": "MathematicsStandard",
        "msb": "MathematicsBasic",
        "mss": "MathematicsStandard",
        "english": "English",
        "englishl": "EnglishLanguageLiterature",
        "englishll": "EnglishLanguageLiterature",
        "englishcommunicative": "EnglishCommunicative",
        "englishcomm": "EnglishCommunicative",
        "eng": "English",
        "tamil": "Tamil",
        "informationtechnology": "InformationTechnology",
        "it": "InformationTechnology",
    }
    return mapping.get(key, value)


def _infer_subject(source_type: str, parts: list[str], file_name: str) -> str:
    if source_type == "TextBooks" and len(parts) > 1:
        return _normalize_subject(parts[1])

    rel_tokens = [p for p in parts[1:] if not re.search(r"^20\d{2}$", p)]
    if source_type == "MarkingScheme" and rel_tokens:
        return _normalize_subject(rel_tokens[0])

    filename_stem = os.path.splitext(file_name)[0].lower()
    subject_patterns = [
        (r"social[\s_-]*science|^ss\b", "SocialScience"),
        (r"\bsst\b", "SocialScience"),
        (r"science", "Science"),
        (r"math(s|ematics)?[\s_-]*standard", "MathematicsStandard"),
        (r"math(s|ematics)?[\s_-]*basic", "MathematicsBasic"),
        (r"math|mathematics", "Mathematics"),
        (r"english[\s_-]*comm", "EnglishCommunicative"),
        (r"english[\s_-]*(ll|l(?![a-z]))", "EnglishLanguageLiterature"),
        (r"english", "English"),
        (r"information[\s_-]*technology|^it\b", "InformationTechnology"),
        (r"tamil", "Tamil"),
    ]
    for pattern, label in subject_patterns:
        if re.search(pattern, filename_stem):
            return label

    for token in rel_tokens:
        normalized = _normalize_subject(token)
        if normalized != token:
            return normalized

    return "General"


def _infer_metadata(file_path: str, root_path: str) -> dict[str, Any]:
    rel_path = os.path.relpath(file_path, root_path)
    parts = rel_path.split(os.sep)
    source_type = _infer_source_type(parts, os.path.basename(file_path))
    file_name = os.path.basename(file_path)
    subject = _infer_subject(source_type, parts, file_name)
    year = _extract_year(parts, file_name)

    return {
        "source_type": source_type,
        "subject": subject,
        "year": year,
        "file_path": file_path.replace("\\", "/"),
        "relative_path": rel_path.replace("\\", "/"),
        "file_name": file_name,
    }


def ingest_pdf(file_path: str, root_path: str) -> int:
    metadata = _infer_metadata(file_path, root_path)
    added = 0

    try:
        with pdfplumber.open(file_path) as pdf:
            for page_idx, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if not text.strip():
                    continue
                chunks = split_text(text)
                for chunk_idx, chunk in enumerate(chunks, start=1):
                    chunk_meta = dict(metadata)
                    chunk_meta["page_no"] = page_idx
                    chunk_meta["chunk_id"] = chunk_idx
                    add_document(chunk, chunk_meta)
                    added += 1
    except Exception:
        # Skip unreadable files and continue ingesting.
        return 0

    return added


def _iter_supported_files(root_path: str) -> list[str]:
    files = []
    for current_root, _, names in os.walk(root_path):
        for name in names:
            ext = os.path.splitext(name)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                files.append(os.path.join(current_root, name))
    return sorted(files)


def ingest_folder(root_path: str, reset: bool = True) -> dict[str, Any]:
    if not os.path.isdir(root_path):
        raise FileNotFoundError(f"Folder not found: {root_path}")

    if reset:
        clear_store()

    files = _iter_supported_files(root_path)
    files_indexed = 0
    chunks_added = 0

    for file_path in files:
        added = ingest_pdf(file_path, root_path)
        if added > 0:
            files_indexed += 1
            chunks_added += added

    save_store()
    return {
        "root_path": root_path.replace("\\", "/"),
        "files_scanned": len(files),
        "files_indexed": files_indexed,
        "chunks_added": chunks_added,
        "total_chunks_in_store": count_documents(),
        "reset": reset,
    }


if __name__ == "__main__":
    summary = ingest_folder(os.path.join("data", "CBSE X"), reset=True)
    print(summary)
