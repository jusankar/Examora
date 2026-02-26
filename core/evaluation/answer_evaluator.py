import json
import os
import re
import shutil
import uuid
from datetime import datetime
from typing import Any

import fitz
import pytesseract
from PIL import Image

from infrastructure.llm import generate

EVALUATION_ROOT = os.path.join("data", "evaluations")


def _ensure_evaluation_root() -> None:
    os.makedirs(EVALUATION_ROOT, exist_ok=True)


def _extract_json(text: str) -> dict[str, Any] | None:
    body = text.strip()
    if body.startswith("{") and body.endswith("}"):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{[\s\S]*\}", body)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _ocr_page(page: fitz.Page) -> tuple[str, list[dict[str, Any]]]:
    pix = page.get_pixmap(dpi=220, alpha=False)
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    raw = pytesseract.image_to_string(image)
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    words = []
    for idx, text in enumerate(data.get("text", [])):
        word = str(text).strip()
        conf = float(data["conf"][idx]) if str(data["conf"][idx]).strip() not in {"-1", ""} else -1
        if not word or conf < 30:
            continue
        words.append(
            {
                "text": word,
                "left": int(data["left"][idx]),
                "top": int(data["top"][idx]),
                "width": int(data["width"][idx]),
                "height": int(data["height"][idx]),
            }
        )
    return raw, words


def _ocr_pdf(answer_pdf_path: str) -> tuple[str, list[dict[str, Any]]]:
    doc = fitz.open(answer_pdf_path)
    page_records = []
    full_text_parts = []
    try:
        for i, page in enumerate(doc, start=1):
            text, words = _ocr_page(page)
            full_text_parts.append(f"[Page {i}]\n{text}")
            page_records.append({"page_no": i, "words": words, "text": text})
    finally:
        doc.close()
    return "\n\n".join(full_text_parts), page_records


def _evaluate_answers(question_paper_text: str, answer_text: str, max_total_marks: int | None) -> dict[str, Any]:
    max_total = max_total_marks if max_total_marks is not None else 80
    prompt = f"""
You are a strict CBSE Class X evaluator.
Evaluate student answers from OCR text against the teacher question paper.

Teacher question paper:
{question_paper_text}

Student OCR answer text:
{answer_text}

Return only valid JSON with this structure:
{{
  "total_marks": <number>,
  "max_marks": {max_total},
  "items": [
    {{
      "qno": "1",
      "status": "correct|partial|incorrect",
      "awarded": 0,
      "max_marks": 1,
      "remark": "short reason",
      "symbol": "✓|~|✗"
    }}
  ],
  "summary": "1-2 line overall feedback"
}}

Rules:
- Keep total_marks as sum(items.awarded).
- Use symbol: correct=✓, partial=~, incorrect=✗
- If an answer is missing, mark incorrect with zero.
"""
    raw = generate(prompt)
    parsed = _extract_json(raw)
    if not parsed:
        return {
            "total_marks": 0,
            "max_marks": max_total,
            "items": [],
            "summary": "Evaluation parsing failed. Please retry.",
        }
    return parsed


def _find_question_anchor(words: list[dict[str, Any]], qno: str) -> tuple[float, float] | None:
    patterns = {f"q{qno}".lower(), f"{qno}.", f"{qno})"}
    for w in words:
        token = str(w["text"]).strip().lower()
        if token in patterns:
            return float(w["left"]), float(w["top"])
    return None


def _annotate_pdf(
    source_pdf_path: str,
    output_pdf_path: str,
    page_ocr: list[dict[str, Any]],
    evaluation: dict[str, Any],
) -> None:
    doc = fitz.open(source_pdf_path)
    items = evaluation.get("items", [])
    max_marks = evaluation.get("max_marks", 80)
    total = evaluation.get("total_marks", 0)

    try:
        if doc.page_count > 0:
            first_page = doc[0]
            header_rect = fitz.Rect(30, 20, first_page.rect.width - 30, 70)
            first_page.draw_rect(header_rect, color=(0.1, 0.3, 0.1), width=1)
            first_page.insert_textbox(
                header_rect,
                f"Total Marks: {total}/{max_marks}",
                fontsize=14,
                fontname="helv",
                align=1,
                color=(0.1, 0.3, 0.1),
            )

        # Put per-question marks near detected question anchors when possible.
        for item in items:
            qno = str(item.get("qno", "")).strip()
            symbol = item.get("symbol", "~")
            awarded = item.get("awarded", 0)
            qmax = item.get("max_marks", "")
            remark = item.get("remark", "")
            annotation_text = f"{symbol} {awarded}/{qmax} {remark}".strip()

            placed = False
            for page_index, record in enumerate(page_ocr):
                anchor = _find_question_anchor(record.get("words", []), qno)
                if not anchor:
                    continue
                page = doc[page_index]
                x, y = anchor
                rect = fitz.Rect(x + 180, y - 4, x + 390, y + 28)
                page.draw_rect(rect, color=(0.1, 0.2, 0.6), width=0.7)
                page.insert_textbox(
                    rect,
                    annotation_text,
                    fontsize=9,
                    fontname="helv",
                    color=(0.1, 0.2, 0.6),
                    align=0,
                )
                placed = True
                break

            if not placed and doc.page_count > 0:
                # Fallback: list in right margin of first page.
                page = doc[0]
                base_y = 86 + (items.index(item) * 18)
                rect = fitz.Rect(page.rect.width - 220, base_y, page.rect.width - 20, base_y + 15)
                page.insert_textbox(
                    rect,
                    f"Q{qno}: {annotation_text}",
                    fontsize=8.5,
                    fontname="helv",
                    color=(0.3, 0.1, 0.4),
                )

        doc.save(output_pdf_path)
    finally:
        doc.close()


def evaluate_answer_sheet(
    answer_pdf_path: str,
    question_paper_text: str,
    max_total_marks: int | None = None,
    question_paper_id: str | None = None,
) -> dict[str, Any]:
    _ensure_evaluation_root()
    evaluation_id = datetime.utcnow().strftime("%Y%m%d%H%M%S") + "_" + uuid.uuid4().hex[:8]
    run_dir = os.path.join(EVALUATION_ROOT, evaluation_id)
    os.makedirs(run_dir, exist_ok=True)

    source_pdf = os.path.join(run_dir, "answer_sheet.pdf")
    with open(answer_pdf_path, "rb") as src, open(source_pdf, "wb") as dst:
        dst.write(src.read())

    answer_text, page_ocr = _ocr_pdf(source_pdf)
    evaluation = _evaluate_answers(question_paper_text, answer_text, max_total_marks)

    corrected_pdf = os.path.join(run_dir, "corrected_answer_sheet.pdf")
    _annotate_pdf(source_pdf, corrected_pdf, page_ocr, evaluation)

    evaluation_payload = {
        "evaluation_id": evaluation_id,
        "question_paper_id": question_paper_id,
        "ocr_text": answer_text,
        "evaluation": evaluation,
        "corrected_pdf_path": corrected_pdf.replace("\\", "/"),
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    result_path = os.path.join(run_dir, "result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(evaluation_payload, f, ensure_ascii=True, indent=2)

    return evaluation_payload


def get_evaluation_result(evaluation_id: str) -> dict[str, Any]:
    result_path = os.path.join(EVALUATION_ROOT, evaluation_id, "result.json")
    if not os.path.exists(result_path):
        raise FileNotFoundError(f"Evaluation not found: {evaluation_id}")
    with open(result_path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_evaluations() -> list[dict[str, Any]]:
    _ensure_evaluation_root()
    records = []
    for folder in os.listdir(EVALUATION_ROOT):
        path = os.path.join(EVALUATION_ROOT, folder, "result.json")
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            ev = data.get("evaluation", {})
            records.append(
                {
                    "evaluation_id": data.get("evaluation_id", folder),
                    "question_paper_id": data.get("question_paper_id"),
                    "created_at": data.get("created_at"),
                    "total_marks": ev.get("total_marks"),
                    "max_marks": ev.get("max_marks"),
                    "summary": ev.get("summary", ""),
                    "corrected_pdf_url": f"/evaluation/{data.get('evaluation_id', folder)}/corrected-pdf",
                }
            )
        except json.JSONDecodeError:
            continue
    records.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return records


def delete_evaluation(evaluation_id: str) -> None:
    run_dir = os.path.join(EVALUATION_ROOT, evaluation_id)
    if not os.path.isdir(run_dir):
        raise FileNotFoundError(f"Evaluation not found: {evaluation_id}")
    shutil.rmtree(run_dir)
