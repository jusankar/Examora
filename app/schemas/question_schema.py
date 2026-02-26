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


class PaperRequest(BaseModel):
    subject: str
    full_portion: bool = True
    chapters: list[str] = []
    marks_options: list[int] = Field(default_factory=lambda: [1, 2, 3, 5])
    difficulty: str = "moderate"
    question_type: str = "board-mix"
    additional_instructions: str | None = None
    save_paper: bool = True
    paper_name: str | None = None
