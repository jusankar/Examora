import json
import os
import shutil
import uuid
from datetime import datetime
from typing import Any

PAPER_ROOT = os.path.join("data", "question_papers")


def _ensure_root() -> None:
    os.makedirs(PAPER_ROOT, exist_ok=True)


def save_question_paper(
    subject: str,
    payload: dict[str, Any],
    config: dict[str, Any],
    paper_name: str | None = None,
) -> dict[str, Any]:
    _ensure_root()
    paper_id = datetime.utcnow().strftime("%Y%m%d%H%M%S") + "_" + uuid.uuid4().hex[:8]
    run_dir = os.path.join(PAPER_ROOT, paper_id)
    os.makedirs(run_dir, exist_ok=True)

    title = paper_name or payload.get("paper", {}).get("title") or f"{subject} Question Paper"
    record = {
        "paper_id": paper_id,
        "title": title,
        "subject": subject,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "config": config,
        "paper": payload.get("paper", {}),
        "markdown": payload.get("markdown", ""),
        "html": payload.get("html", ""),
    }
    with open(os.path.join(run_dir, "paper.json"), "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=True, indent=2)
    return {
        "paper_id": paper_id,
        "title": title,
        "subject": subject,
        "created_at": record["created_at"],
    }


def get_question_paper(paper_id: str) -> dict[str, Any]:
    path = os.path.join(PAPER_ROOT, paper_id, "paper.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Question paper not found: {paper_id}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_question_papers() -> list[dict[str, Any]]:
    _ensure_root()
    records = []
    for folder in os.listdir(PAPER_ROOT):
        json_path = os.path.join(PAPER_ROOT, folder, "paper.json")
        if not os.path.exists(json_path):
            continue
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            records.append(
                {
                    "paper_id": data.get("paper_id", folder),
                    "title": data.get("title", "Untitled"),
                    "subject": data.get("subject", "Unknown"),
                    "created_at": data.get("created_at"),
                }
            )
        except json.JSONDecodeError:
            continue
    records.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return records


def delete_question_paper(paper_id: str) -> None:
    run_dir = os.path.join(PAPER_ROOT, paper_id)
    if not os.path.isdir(run_dir):
        raise FileNotFoundError(f"Question paper not found: {paper_id}")
    shutil.rmtree(run_dir)
