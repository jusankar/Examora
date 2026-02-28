def test_home_route(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Examora API is running. Open /teacher for UI."


def test_generate_question_route(client) -> None:
    response = client.post(
        "/generate-question",
        json={"query": "What is Newton's second law?", "subject": "Science", "marks": 2},
    )
    assert response.status_code == 200
    assert "mock-question:What is Newton's second law?" == response.json()["question"]


def test_subjects_and_chapters_routes(client) -> None:
    subjects_response = client.get("/subjects")
    assert subjects_response.status_code == 200
    assert subjects_response.json()["subjects"] == ["Science", "Mathematics"]

    chapters_response = client.get("/chapters/Science")
    assert chapters_response.status_code == 200
    assert chapters_response.json()["chapters"] == ["Chapter 1"]


def test_generate_and_list_papers(client) -> None:
    payload = {
        "subject": "Science",
        "full_portion": True,
        "chapters": [],
        "marks_options": [1, 2],
        "difficulty": "moderate",
        "question_type": "board-mix",
        "additional_instructions": None,
        "save_paper": True,
        "paper_name": "Unit Test",
    }
    response = client.post("/generate-paper", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["saved_paper"]["paper_id"] == "paper_001"

    papers_response = client.get("/papers")
    assert papers_response.status_code == 200
    assert len(papers_response.json()["papers"]) == 1


def test_evaluation_rejects_non_pdf_upload(client) -> None:
    response = client.post(
        "/evaluation/evaluate-answer-sheet",
        files={"answer_pdf": ("answers.txt", b"plain text", "text/plain")},
        data={"question_paper_text": "x" * 30, "max_total_marks": "80"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF is supported."


def test_evaluation_requires_question_source(client) -> None:
    response = client.post(
        "/evaluation/evaluate-answer-sheet",
        files={"answer_pdf": ("answers.pdf", b"%PDF-1.4 mock", "application/pdf")},
        data={"max_total_marks": "80"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "question_paper_id or question_paper_text is required."


def test_evaluation_with_question_text(client) -> None:
    response = client.post(
        "/evaluation/evaluate-answer-sheet",
        files={"answer_pdf": ("answers.pdf", b"%PDF-1.4 mock", "application/pdf")},
        data={"question_paper_text": "This is a complete mock question paper text.", "max_total_marks": "10"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["evaluation_id"] == "ev_test_001"
    assert payload["total_marks"] == 7
    assert payload["max_marks"] == 10


def test_evaluation_listing_route(client) -> None:
    response = client.get("/evaluation")
    assert response.status_code == 200
    evaluations = response.json()["evaluations"]
    assert len(evaluations) == 1
    assert evaluations[0]["evaluation_id"] == "ev_test_001"
