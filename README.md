# Examora

Examora is a CBSE Class X assistant that generates question papers and evaluates scanned answer sheets using a small RAG pipeline plus LLM prompting. It ships with a teacher-facing UI and a FastAPI backend.

**What It Does**
- Ingests CBSE source PDFs (textbooks, PYQs, SQPs, marking schemes, curriculum) into a local FAISS vector store.
- Generates single questions or full papers in Markdown/JSON/HTML.
- Evaluates uploaded answer-sheet PDFs with OCR and returns marks, feedback, and a corrected PDF overlay.

**Project Layout**
- `app/` FastAPI app and routes.
- `core/` RAG pipeline and evaluation logic.
- `infrastructure/` LLM, embeddings, vector store utilities.
- `frontend/` legacy static UI.
- `frontend-shadcn/` Vite + Shadcn UI (preferred).
- `data/` local storage for vector store, papers, evaluations, and source PDFs.

**Requirements**
- Python 3.11+
- Node 20+ if you want to build the Shadcn UI
- Tesseract OCR installed and on PATH for answer-sheet evaluation
- An OpenAI API key in `.env` as `OPENAI_API_KEY`

**Quickstart (Local)**
1. Create a virtual environment and install backend deps.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Set your API key.

```bash
setx OPENAI_API_KEY "your_key_here"
```

3. Run the API.

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. Open the UI.

```text
http://localhost:8000/teacher
```

**Build The Shadcn UI (Optional)**
1. Install UI dependencies and build.

```bash
cd frontend-shadcn
corepack enable
yarn install --frozen-lockfile
yarn build
```

2. Restart the API so it serves `frontend-shadcn/dist`.

**Docker**
1. Build and start.

```bash
docker compose up --build
```

2. Open the UI at `http://localhost:8000/teacher`.

**API Overview**
- `POST /ingest` Ingest PDFs from a folder, default `data/CBSE X`.
- `GET /stats` Vector store statistics.
- `GET /subjects` Supported subjects for paper generation.
- `GET /chapters/{subject}` Chapters for a subject.
- `POST /generate-question` Generate a single question from a prompt.
- `POST /generate-paper` Generate a full paper and optional save.
- `GET /papers` List saved papers.
- `GET /papers/{paper_id}` Fetch a saved paper.
- `DELETE /papers/{paper_id}` Delete a saved paper.
- `POST /evaluation/evaluate-answer-sheet` Evaluate an answer sheet PDF with a question paper.
- `GET /evaluation/{evaluation_id}` Fetch evaluation details.
- `GET /evaluation` List evaluations.
- `GET /evaluation/{evaluation_id}/corrected-pdf` Download annotated PDF.
- `DELETE /evaluation/{evaluation_id}` Delete an evaluation.

**Data Storage**
- `data/.vector_store/` FAISS index and metadata.
- `data/question_papers/` Generated paper JSON/HTML/Markdown.
- `data/evaluations/` OCR text, evaluation JSON, corrected PDFs.

**Tests**
1. Install dev deps and run tests.

```bash
pip install -r requirements-dev.txt
pytest
```

**Notes**
- The backend currently uses the `gpt-4o-mini` model (see `infrastructure/llm.py`).
- If you do not build the Shadcn UI, the app serves the legacy UI from `frontend/`.
