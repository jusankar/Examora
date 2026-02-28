import json
import os
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from core.evaluation.answer_evaluator import (
    delete_evaluation,
    evaluate_answer_sheet,
    get_evaluation_result,
    list_evaluations,
)
from core.rag.paper_library import get_question_paper

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.post("/evaluate-answer-sheet")
async def evaluate_sheet(
    answer_pdf: UploadFile = File(...),
    question_paper_text: str | None = Form(default=None),
    question_paper_id: str | None = Form(default=None),
    max_total_marks: int = Form(80),
):
    if answer_pdf.content_type not in {"application/pdf"}:
        raise HTTPException(status_code=400, detail="Only PDF is supported.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(await answer_pdf.read())
        temp_path = temp_file.name

    resolved_question_text = (question_paper_text or "").strip()
    if question_paper_id:
        try:
            paper = get_question_paper(question_paper_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        resolved_question_text = paper.get("markdown", "") or json.dumps(paper.get("paper", {}), ensure_ascii=True)

    if not resolved_question_text:
        raise HTTPException(status_code=400, detail="question_paper_id or question_paper_text is required.")

    try:
        result = evaluate_answer_sheet(
            answer_pdf_path=temp_path,
            question_paper_text=resolved_question_text,
            max_total_marks=max_total_marks,
            question_paper_id=question_paper_id,
        )
        evaluation_id = result["evaluation_id"]
        return {
            "status": "ok",
            "evaluation_id": evaluation_id,
            "total_marks": result["evaluation"].get("total_marks", 0),
            "max_marks": result["evaluation"].get("max_marks", max_total_marks),
            "summary": result["evaluation"].get("summary", ""),
            "items": result["evaluation"].get("items", []),
            "corrected_pdf_url": f"/evaluation/{evaluation_id}/corrected-pdf",
        }
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@router.get("/{evaluation_id}")
def get_result(evaluation_id: str):
    try:
        payload = get_evaluation_result(evaluation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok", **payload}


@router.get("")
def list_results():
    return {"status": "ok", "evaluations": list_evaluations()}


@router.get("/{evaluation_id}/corrected-pdf")
def get_corrected_pdf(evaluation_id: str):
    try:
        payload = get_evaluation_result(evaluation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    pdf_path = payload.get("corrected_pdf_path")
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Corrected PDF not found.")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"{evaluation_id}_corrected.pdf",
        content_disposition_type="inline",
    )


@router.delete("/{evaluation_id}")
def remove_result(evaluation_id: str):
    try:
        delete_evaluation(evaluation_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok", "deleted": evaluation_id}
