from fastapi import APIRouter, HTTPException
from app.schemas.question_schema import IngestRequest, PaperRequest, QuestionRequest
from core.rag.ingest import ingest_folder
from core.rag.generator import generate_question
from core.rag.paper_library import delete_question_paper, get_question_paper, list_question_papers, save_question_paper
from core.rag.paper_generator import (
    generate_paper,
    get_chapters_for_subject,
    get_supported_subjects,
)
from infrastructure.vector_store import get_store_stats

router = APIRouter()

@router.post("/generate-question")
def generate(req: QuestionRequest):
    result = generate_question(
        query=req.query,
        subject=req.subject,
        section=req.section,
        marks=req.marks,
        difficulty=req.difficulty,
        question_type=req.question_type,
    )
    return {"question": result}


@router.post("/ingest")
def ingest(req: IngestRequest):
    summary = ingest_folder(req.path, reset=req.reset)
    return {"status": "ok", "summary": summary}


@router.get("/stats")
def stats():
    return {"status": "ok", "summary": get_store_stats()}


@router.get("/subjects")
def subjects():
    return {"status": "ok", "subjects": get_supported_subjects()}


@router.get("/chapters/{subject}")
def chapters(subject: str):
    return {"status": "ok", "subject": subject, "chapters": get_chapters_for_subject(subject)}


@router.post("/generate-paper")
def build_paper(req: PaperRequest):
    result = generate_paper(req.model_dump())
    saved = None
    if req.save_paper:
        saved = save_question_paper(
            subject=req.subject,
            payload=result,
            config=req.model_dump(),
            paper_name=req.paper_name,
        )
    return {"status": "ok", **result, "saved_paper": saved}


@router.get("/papers")
def list_papers():
    return {"status": "ok", "papers": list_question_papers()}


@router.get("/papers/{paper_id}")
def get_paper(paper_id: str):
    try:
        paper = get_question_paper(paper_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok", "paper": paper}


@router.delete("/papers/{paper_id}")
def delete_paper(paper_id: str):
    try:
        delete_question_paper(paper_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok", "deleted": paper_id}
