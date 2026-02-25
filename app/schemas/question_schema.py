from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    query: str = Field(..., min_length=3)
    subject: str | None = None
    section: str | None = None
    marks: int | None = Field(default=None, ge=1, le=20)
    difficulty: str | None = None
    question_type: str | None = None


class IngestRequest(BaseModel):
    path: str = "data/CBSE X"
    reset: bool = True
