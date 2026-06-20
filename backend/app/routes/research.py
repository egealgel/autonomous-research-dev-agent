import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.orm import Session

from app.db import get_db
from app.jobs import process_research_task
from app.models import Task, TaskStatus
from app.queue import research_queue

router = APIRouter(prefix="/research", tags=["research"])


class ResearchCreate(BaseModel):
    prompt: str = Field(min_length=1, max_length=10_000)
    urls: list[HttpUrl] = Field(min_length=1, max_length=10)


class ResearchAccepted(BaseModel):
    task_id: uuid.UUID
    job_id: str
    status: str


@router.post("", response_model=ResearchAccepted, status_code=202)
def create_research(payload: ResearchCreate, db: Session = Depends(get_db)) -> ResearchAccepted:
    task = Task(
        prompt=payload.prompt,
        agent="research",
        status=TaskStatus.pending,
        params={"urls": [str(u) for u in payload.urls]},
        created_at=datetime.now(timezone.utc),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    job = research_queue.enqueue(process_research_task, str(task.id), job_id=f"research-{task.id}")
    return ResearchAccepted(task_id=task.id, job_id=job.id, status=task.status)


@router.get("/{task_id}")
def get_research(task_id: str, db: Session = Depends(get_db)):
    task = db.get(Task, uuid.UUID(task_id))
    if task is None or task.agent != "research":
        raise HTTPException(status_code=404, detail="Research task not found")
    return {
        "id": str(task.id),
        "status": task.status,
        "prompt": task.prompt,
        "params": task.params,
        "result_text": task.result_text,
        "result_path": task.result_path,
        "error": task.error,
        "created_at": task.created_at,
        "completed_at": task.completed_at,
    }
