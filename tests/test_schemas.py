import pytest
from pydantic import ValidationError

from app.schemas.evaluation_schema import EvaluationRequest
from app.schemas.question_schema import PaperRequest, QuestionRequest


def test_question_request_accepts_valid_payload() -> None:
    payload = QuestionRequest(query="Explain photosynthesis", marks=5, subject="Science")
    assert payload.query == "Explain photosynthesis"
    assert payload.marks == 5


def test_question_request_rejects_invalid_marks() -> None:
    with pytest.raises(ValidationError):
        QuestionRequest(query="Valid query", marks=0)


def test_evaluation_request_enforces_min_question_text() -> None:
    with pytest.raises(ValidationError):
        EvaluationRequest(question_paper_text="too short", max_total_marks=80)


def test_paper_request_default_marks_options() -> None:
    payload = PaperRequest(subject="Science")
    assert payload.marks_options == [1, 2, 3, 5]
