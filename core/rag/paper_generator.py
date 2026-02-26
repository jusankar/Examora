import json
import re
from typing import Any

from infrastructure.llm import generate

SUBJECT_CHAPTERS: dict[str, list[str]] = {
    "Science": [
        "Chemical Reactions and Equations",
        "Acids, Bases and Salts",
        "Metals and Non-Metals",
        "Carbon and Its Compounds",
        "Life Processes",
        "Control and Coordination",
        "How Do Organisms Reproduce?",
        "Heredity and Evolution",
        "Light - Reflection and Refraction",
        "Human Eye and Colourful World",
        "Electricity",
        "Magnetic Effects of Electric Current",
        "Our Environment",
    ],
    "Mathematics": [
        "Real Numbers",
        "Polynomials",
        "Pair of Linear Equations in Two Variables",
        "Quadratic Equations",
        "Arithmetic Progressions",
        "Triangles",
        "Coordinate Geometry",
        "Trigonometry",
        "Applications of Trigonometry",
        "Circles",
        "Areas Related to Circles",
        "Surface Areas and Volumes",
        "Statistics",
        "Probability",
    ],
    "SocialScience": [
        "The Rise of Nationalism in Europe",
        "Nationalism in India",
        "The Making of a Global World",
        "Print Culture and the Modern World",
        "Resources and Development",
        "Forest and Wildlife Resources",
        "Water Resources",
        "Agriculture",
        "Minerals and Energy Resources",
        "Manufacturing Industries",
        "Lifelines of National Economy",
        "Power Sharing",
        "Federalism",
        "Gender, Religion and Caste",
        "Political Parties",
        "Outcomes of Democracy",
    ],
    "EnglishLanguageLiterature": [
        "First Flight Prose",
        "First Flight Poems",
        "Footprints Without Feet",
        "Reading Comprehension",
        "Writing Skills",
        "Grammar",
    ],
    "EnglishCommunicative": [
        "Reading Skills",
        "Writing Skills",
        "Grammar",
        "Literature",
    ],
    "Tamil": [
        "Prose",
        "Poetry",
        "Grammar",
        "Composition",
    ],
    "InformationTechnology": [
        "Digital Documentation",
        "Electronic Spreadsheet",
        "Database Management",
        "Web Applications and Security",
    ],
}


def get_supported_subjects() -> list[str]:
    return sorted(SUBJECT_CHAPTERS.keys())


def get_chapters_for_subject(subject: str) -> list[str]:
    return SUBJECT_CHAPTERS.get(subject, [])


def _merge_unique_context(*context_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def _format_context(context_items: list[dict[str, Any]]) -> str:
    lines = []
    for idx, item in enumerate(context_items, start=1):
        metadata = item.get("metadata", {})
        line = (
            f"[{idx}] {metadata.get('source_type', 'Unknown')} | "
            f"{metadata.get('subject', 'General')} | "
            f"{metadata.get('year', 'NA')} | "
            f"page {metadata.get('page_no', 'NA')} | "
            f"{metadata.get('file_name', 'unknown')}\n"
            f"{item.get('text', '')}"
        )
        lines.append(line)
    return "\n\n".join(lines)


def _extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _build_markdown(paper: dict[str, Any]) -> str:
    title = paper.get("title", "CBSE Class X Question Paper")
    subject = paper.get("subject", "Not specified")
    time_allowed = paper.get("time_allowed", "3 Hours")
    max_marks = paper.get("max_marks", "80")

    lines = [
        f"# {title}",
        "",
        f"**Subject:** {subject}",
        f"**Time Allowed:** {time_allowed}",
        f"**Maximum Marks:** {max_marks}",
        "",
        "## General Instructions",
    ]

    for item in paper.get("instructions", []):
        lines.append(f"- {item}")

    for section in paper.get("sections", []):
        lines.append("")
        lines.append(f"## {section.get('name', 'Section')}")
        for question in section.get("questions", []):
            qno = question.get("qno", "")
            marks = question.get("marks", "")
            text = question.get("text", "")
            lines.append(f"{qno}. {text} *({marks} mark{'s' if marks != 1 else ''})*")

            passage = question.get("passage")
            if passage:
                lines.append(f"   **Passage:** {passage}")

            case_study = question.get("case_study")
            if case_study:
                lines.append(f"   **Case Study:** {case_study}")

            options = question.get("options", [])
            if isinstance(options, list) and options:
                lines.append("   **Options:**")
                for idx, option in enumerate(options):
                    label = chr(65 + idx)
                    lines.append(f"   - ({label}) {option}")

            for sub in question.get("sub_questions", []):
                if isinstance(sub, dict):
                    sub_qno = sub.get("sub_qno", "")
                    sub_text = sub.get("text", "")
                    sub_marks = sub.get("marks")
                    if sub_marks is not None:
                        lines.append(
                            f"   - ({sub_qno}) {sub_text} *({sub_marks} mark{'s' if sub_marks != 1 else ''})*"
                        )
                    else:
                        lines.append(f"   - ({sub_qno}) {sub_text}")
                else:
                    lines.append(f"   - {sub}")

    notes = paper.get("source_notes", [])
    if notes:
        lines.append("")
        lines.append("## Source Notes")
        for note in notes:
            lines.append(f"- {note}")

    return "\n".join(lines)


def _markdown_to_html(markdown: str) -> str:
    html_lines = []
    in_list = False

    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<p></p>")
            continue

        if line.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{line[2:]}</li>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            paragraph = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", line)
            paragraph = re.sub(r"\*(.*?)\*", r"<em>\1</em>", paragraph)
            html_lines.append(f"<p>{paragraph}</p>")

    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def _build_printable_html(markdown: str) -> str:
    body = _markdown_to_html(markdown)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CBSE Question Paper</title>
  <style>
    @page {{
      size: A4 portrait;
      margin: 12mm 10mm 14mm 10mm;
    }}
    :root {{
      --ink: #111827;
      --rule: #c7ced9;
      --bg: #f4f7fb;
      --card: #ffffff;
    }}
    body {{
      margin: 0;
      color: var(--ink);
      background: radial-gradient(circle at top right, #dbeafe 0%, var(--bg) 45%, #eef2ff 100%);
      font-family: "Times New Roman", Georgia, serif;
    }}
    .print-area {{
      width: 210mm;
      margin: 12px auto;
    }}
    .page {{
      width: 210mm;
      height: 297mm;
      margin: 0 auto 10px;
      background: var(--card);
      box-shadow: 0 12px 32px rgba(0,0,0,.08);
      padding: 12mm 10mm 14mm;
      box-sizing: border-box;
      display: grid;
      grid-template-rows: 1fr auto;
      page-break-after: always;
    }}
    .page:last-child {{
      page-break-after: auto;
    }}
    .page-body {{
      overflow: hidden;
      height: 100%;
    }}
    .page-footer {{
      border-top: 1px solid var(--rule);
      font-size: 12px;
      color: #475569;
      padding-top: 4px;
      text-align: right;
    }}
    #content-source {{
      visibility: hidden;
      position: absolute;
      left: -10000px;
      top: -10000px;
      width: 190mm;
    }}
    h1 {{
      font-size: 20px;
      text-align: center;
      letter-spacing: .4px;
      text-transform: uppercase;
      margin: 0 0 10px;
      border-bottom: 2px solid var(--rule);
      padding-bottom: 8px;
    }}
    h2 {{
      font-size: 16px;
      margin: 18px 0 8px;
      text-transform: uppercase;
      border-bottom: 1px solid var(--rule);
      padding-bottom: 4px;
    }}
    p, li {{
      font-size: 13.5px;
      line-height: 1.45;
      margin: 0 0 7px;
    }}
    ul {{
      margin: 0 0 10px 18px;
      padding: 0;
    }}
    @media print {{
      body {{
        background: #fff;
      }}
      .print-area {{
        width: auto;
        margin: 0;
      }}
      .page {{
        margin: 0;
        box-shadow: none;
      }}
    }}
  </style>
</head>
<body>
  <div id="content-source">{body}</div>
  <main class="print-area" id="print-area"></main>
  <script>
    (function paginate() {{
      const source = document.getElementById("content-source");
      const output = document.getElementById("print-area");
      const nodes = Array.from(source.children);
      const pages = [];

      function newPage() {{
        const page = document.createElement("section");
        page.className = "page";
        const body = document.createElement("div");
        body.className = "page-body";
        const footer = document.createElement("div");
        footer.className = "page-footer";
        page.appendChild(body);
        page.appendChild(footer);
        output.appendChild(page);
        pages.push({{ page, body, footer }});
        return pages[pages.length - 1];
      }}

      let current = newPage();
      for (const node of nodes) {{
        const clone = node.cloneNode(true);
        current.body.appendChild(clone);
        if (current.body.scrollHeight > current.body.clientHeight) {{
          current.body.removeChild(clone);
          current = newPage();
          current.body.appendChild(clone);
        }}
      }}

      const total = pages.length;
      pages.forEach((p, i) => {{
        p.footer.textContent = `Page ${{i + 1}} of ${{total}}`;
      }});

      window.dispatchEvent(new CustomEvent("examora:paginated", {{ detail: {{ totalPages: total }} }}));
    }})();
  </script>
</body>
</html>
"""


def _normalize_paper_schema(paper: dict[str, Any]) -> dict[str, Any]:
    normalized_sections = []
    for section in paper.get("sections", []):
        normalized_questions = []
        for question in section.get("questions", []):
            normalized_questions.append(
                {
                    "qno": question.get("qno", ""),
                    "marks": question.get("marks", ""),
                    "text": question.get("text", ""),
                    "options": question.get("options", []) if isinstance(question.get("options"), list) else [],
                    "passage": question.get("passage"),
                    "case_study": question.get("case_study"),
                    "sub_questions": question.get("sub_questions", [])
                    if isinstance(question.get("sub_questions"), list)
                    else [],
                }
            )
        normalized_sections.append({"name": section.get("name", "Section"), "questions": normalized_questions})

    return {
        "title": paper.get("title", "CBSE Board Examination - Class X"),
        "subject": paper.get("subject", "Not specified"),
        "time_allowed": paper.get("time_allowed", "3 Hours"),
        "max_marks": paper.get("max_marks", "80"),
        "instructions": paper.get("instructions", []),
        "sections": normalized_sections,
        "source_notes": paper.get("source_notes", []),
    }


def _paper_has_missing_artifacts(paper: dict[str, Any]) -> bool:
    keywords = ("following", "passage", "case study", "based on the above")
    for section in paper.get("sections", []):
        for question in section.get("questions", []):
            text = str(question.get("text", "")).lower()
            has_options = bool(question.get("options"))
            has_passage = bool(question.get("passage"))
            has_case = bool(question.get("case_study"))
            has_sub = bool(question.get("sub_questions"))

            if "which of the following" in text and not has_options:
                return True
            if "read the given passage" in text and not has_passage:
                return True
            if "study the case study" in text and not has_case:
                return True
            if any(key in text for key in keywords) and not (has_options or has_passage or has_case or has_sub):
                return True
    return False


def generate_paper(payload: dict[str, Any]) -> dict[str, Any]:
    from core.rag.retriever import retrieve_context

    subject = payload.get("subject")
    full_portion = payload.get("full_portion", True)
    chapters = payload.get("chapters", [])
    marks_options = sorted({int(v) for v in payload.get("marks_options", [1, 2, 3, 5])})
    difficulty = payload.get("difficulty", "moderate")
    question_type = payload.get("question_type", "board-mix")
    additional_instructions = payload.get("additional_instructions") or ""

    chapter_clause = "all prescribed chapters" if full_portion else ", ".join(chapters)
    query = (
        f"Create a full CBSE Class 10 {subject} question paper using chapters: {chapter_clause}. "
        f"Include marks only from {marks_options}. Difficulty {difficulty}. Type {question_type}."
    )

    base_filters = {"subject": subject}
    textbooks = retrieve_context(query, top_k=8, filters={**base_filters, "source_types": ["TextBooks"]})
    pyq = retrieve_context(query, top_k=5, filters={**base_filters, "source_types": ["PYQ"]})
    sqp = retrieve_context(query, top_k=5, filters={**base_filters, "source_types": ["SQP"]})
    marking_scheme = retrieve_context(query, top_k=5, filters={**base_filters, "source_types": ["MarkingScheme"]})
    curriculum = retrieve_context(query, top_k=3, filters={**base_filters, "source_types": ["Curriculum"]})
    fallback = retrieve_context(query, top_k=4, filters=base_filters)

    context = _merge_unique_context(textbooks, pyq, sqp, marking_scheme, curriculum, fallback)[:20]
    context_text = _format_context(context)

    prompt = f"""
You are an expert CBSE Class X paper setter.
Use the retrieved context to produce a board-style paper with realistic structure and phrasing.
Strictly consider source priorities:
1) TextBooks content correctness
2) PYQ repeat patterns
3) SQP paper style
4) MarkingScheme answer depth and distribution
5) Curriculum/weightage balance

Teacher selection:
- Subject: {subject}
- Full Portion: {full_portion}
- Chapters: {chapters}
- Allowed Marks per question: {marks_options}
- Difficulty: {difficulty}
- Question type bias: {question_type}
- Additional instructions: {additional_instructions}

Retrieved context:
{context_text}

Return ONLY valid JSON with schema:
{{
  "title": "CBSE Board Examination - Class X",
  "subject": "<subject>",
  "time_allowed": "3 Hours",
  "max_marks": "<number>",
  "instructions": ["..."],
  "sections": [
    {{
      "name": "Section A",
      "questions": [
        {{
          "qno": 1,
          "marks": 1,
          "text": "...",
          "options": ["...", "..."],
          "passage": "...",
          "case_study": "...",
          "sub_questions": [{{"sub_qno": "a", "text": "...", "marks": 2}}]
        }}
      ]
    }}
  ],
  "source_notes": ["cite source categories and rationale in short bullets"]
}}

Rules:
- Never produce dangling references like "following" without options/list.
- If question asks for passage/case study, include full passage/case_study field.
- Use options field for MCQ questions.
- Keep JSON valid and complete.
"""

    raw = generate(prompt)
    parsed = _extract_json(raw)
    if parsed:
        parsed = _normalize_paper_schema(parsed)
        if _paper_has_missing_artifacts(parsed):
            retry_prompt = prompt + "\nFix missing artifacts and regenerate complete JSON."
            retry_raw = generate(retry_prompt)
            retry_parsed = _extract_json(retry_raw)
            if retry_parsed:
                parsed = _normalize_paper_schema(retry_parsed)

    if not parsed:
        parsed = {
            "title": "CBSE Board Examination - Class X",
            "subject": subject,
            "time_allowed": "3 Hours",
            "max_marks": "80",
            "instructions": ["Unable to parse model JSON. Regenerate the paper."],
            "sections": [{"name": "Generated Content", "questions": [{"qno": 1, "marks": 0, "text": raw, "sub_questions": []}]}],
            "source_notes": ["Fallback output due to parsing issue."],
        }

    markdown = _build_markdown(parsed)
    html = _build_printable_html(markdown)
    return {"paper": parsed, "markdown": markdown, "html": html}
