from pydantic import BaseModel, Field


class EvaluationRequest(BaseModel):
    question_paper_text: str = Field(..., min_length=20)
    max_total_marks: int | None = Field(default=80, ge=1, le=200)
