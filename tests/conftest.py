import sys
import types
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient


def _install_test_doubles() -> None:
    generator_mod = types.ModuleType("core.rag.generator")
    generator_mod.generate_question = lambda **kwargs: f"mock-question:{kwargs.get('query', '')}"
    sys.modules["core.rag.generator"] = generator_mod

    ingest_mod = types.ModuleType("core.rag.ingest")
    ingest_mod.ingest_folder = lambda path, reset=True: {"path": path, "reset": reset}
    sys.modules["core.rag.ingest"] = ingest_mod

    paper_generator_mod = types.ModuleType("core.rag.paper_generator")
    paper_generator_mod.get_supported_subjects = lambda: ["Science", "Mathematics"]
    paper_generator_mod.get_chapters_for_subject = lambda subject: ["Chapter 1"] if subject == "Science" else []
    paper_generator_mod.generate_paper = lambda payload: {
        "paper": {"title": "Mock Paper", "subject": payload.get("subject", "Science")},
        "markdown": "# Mock Paper",
        "html": "<html><body><h1>Mock Paper</h1></body></html>",
    }
    sys.modules["core.rag.paper_generator"] = paper_generator_mod

    vector_store_mod = types.ModuleType("infrastructure.vector_store")
    vector_store_mod.get_store_stats = lambda: {"total_chunks": 0}
    sys.modules["infrastructure.vector_store"] = vector_store_mod

    answer_eval_mod = types.ModuleType("core.evaluation.answer_evaluator")
    answer_eval_mod.evaluate_answer_sheet = (
        lambda answer_pdf_path, question_paper_text, max_total_marks=80, question_paper_id=None: {
            "evaluation_id": "ev_test_001",
            "question_paper_id": question_paper_id,
            "evaluation": {
                "total_marks": 7,
                "max_marks": max_total_marks,
                "summary": "Good attempt.",
                "items": [{"qno": "1", "awarded": 1, "max_marks": 1, "status": "correct"}],
            },
        }
    )
    answer_eval_mod.get_evaluation_result = lambda evaluation_id: {
        "evaluation_id": evaluation_id,
        "evaluation": {"total_marks": 7, "max_marks": 10, "summary": "Good attempt.", "items": []},
        "corrected_pdf_path": __file__,
    }
    answer_eval_mod.list_evaluations = lambda: [
        {"evaluation_id": "ev_test_001", "total_marks": 7, "max_marks": 10, "corrected_pdf_url": "/evaluation/ev_test_001/corrected-pdf"}
    ]
    answer_eval_mod.delete_evaluation = lambda evaluation_id: None
    sys.modules["core.evaluation.answer_evaluator"] = answer_eval_mod

    paper_library_mod = types.ModuleType("core.rag.paper_library")
    papers = {
        "paper_001": {
            "paper_id": "paper_001",
            "title": "Science Mock",
            "subject": "Science",
            "markdown": "# Science Mock",
            "html": "<html><body><h1>Science Mock</h1></body></html>",
            "paper": {"title": "Science Mock"},
        }
    }

    paper_library_mod.save_question_paper = lambda subject, payload, config, paper_name=None: {
        "paper_id": "paper_001",
        "title": paper_name or "Science Mock",
        "subject": subject,
        "created_at": "2026-01-01T00:00:00Z",
    }
    paper_library_mod.list_question_papers = lambda: [
        {"paper_id": "paper_001", "title": "Science Mock", "subject": "Science", "created_at": "2026-01-01T00:00:00Z"}
    ]
    paper_library_mod.get_question_paper = lambda paper_id: papers[paper_id]
    paper_library_mod.delete_question_paper = lambda paper_id: None
    sys.modules["core.rag.paper_library"] = paper_library_mod


@pytest.fixture(scope="session")
def app():
    _install_test_doubles()
    from app.main import app as fastapi_app

    return fastapi_app


@pytest.fixture()
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
