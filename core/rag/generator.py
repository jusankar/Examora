from core.rag.retriever import retrieve_context
from infrastructure.llm import generate


def _merge_unique_context(*context_groups: list[dict]) -> list[dict]:
    seen = set()
    merged = []
    for group in context_groups:
        for item in group:
            key = item.get("index")
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _format_context(context_items: list[dict]) -> str:
    lines = []
    for idx, item in enumerate(context_items, start=1):
        metadata = item.get("metadata", {})
        source_type = metadata.get("source_type", "Unknown")
        subject = metadata.get("subject", "General")
        year = metadata.get("year", "NA")
        page_no = metadata.get("page_no", "NA")
        file_name = metadata.get("file_name", "unknown")
        text = item.get("text", "")
        lines.append(
            f"[{idx}] {source_type} | {subject} | {year} | page {page_no} | {file_name}\n{text}"
        )
    return "\n\n".join(lines)


def generate_question(
    query: str,
    subject: str | None = None,
    section: str | None = None,
    marks: int | None = None,
    difficulty: str | None = None,
    question_type: str | None = None,
):
    base_filters = {"subject": subject} if subject else {}

    textbooks = retrieve_context(
        query,
        top_k=4,
        filters={**base_filters, "source_types": ["TextBooks"]},
    )
    pyq = retrieve_context(
        query,
        top_k=2,
        filters={**base_filters, "source_types": ["PYQ"]},
    )
    sqp = retrieve_context(
        query,
        top_k=2,
        filters={**base_filters, "source_types": ["SQP"]},
    )
    marking_scheme = retrieve_context(
        query,
        top_k=2,
        filters={**base_filters, "source_types": ["MarkingScheme"]},
    )
    curriculum = retrieve_context(
        query,
        top_k=1,
        filters={**base_filters, "source_types": ["Curriculum"]},
    )
    fallback = retrieve_context(query, top_k=3, filters=base_filters)

    context = _merge_unique_context(
        textbooks, pyq, sqp, marking_scheme, curriculum, fallback
    )[:10]
    context_text = _format_context(context)

    prompt = f"""
    You are preparing a Class 10 CBSE question/paper item in Markdown.
    Use all relevant source categories when available:
    - TextBooks for core content accuracy (highest priority)
    - PYQ for repeated question patterns and phrasing
    - SQP for likely paper pattern and style
    - MarkingScheme for answer structure and marks allocation
    - Curriculum for syllabus/weightage alignment

    Constraints:
    - Subject: {subject or "Not specified"}
    - Section: {section or "Not specified"}
    - Marks: {marks if marks is not None else "Not specified"}
    - Difficulty: {difficulty or "Not specified"}
    - Question Type: {question_type or "Not specified"}
    - Follow marking-scheme-compatible wording and expected answer depth.

    Retrieved Context:
    {context_text}

    Instruction:
    {query}

    Return valid Markdown only with these headings:
    ## Question
    ## Marks
    ## Expected Answer Points
    ## Marking Scheme Guidance
    ## Pattern Rationale (PYQ/SQP)
    ## Source Notes

    In Source Notes, reference context items like [1], [2] and mention source type.
    """

    return generate(prompt)
