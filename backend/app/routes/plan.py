import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.orm import Session

from app.agents.planner import PlanType
from app.db import get_db
from app.jobs import process_plan_task
from app.models import Task, TaskStatus
from app.queue import plan_queue

router = APIRouter(prefix="/plan", tags=["plan"])


class PlanCreate(BaseModel):
    prompt: str = Field(min_length=1, max_length=10_000)
    plan_type: PlanType = PlanType.software_roadmap
    urls: list[HttpUrl] = Field(default_factory=list, max_length=10)


class PlanAccepted(BaseModel):
    task_id: uuid.UUID
    job_id: str
    status: str
    plan_type: PlanType


@router.post("", response_model=PlanAccepted, status_code=202)
def create_plan(payload: PlanCreate, db: Session = Depends(get_db)) -> PlanAccepted:
    task = Task(
        prompt=payload.prompt,
        agent="planner",
        status=TaskStatus.pending,
        params={
            "plan_type": payload.plan_type.value,
            "urls": [str(u) for u in payload.urls],
        },
        created_at=datetime.now(timezone.utc),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    job = plan_queue.enqueue(process_plan_task, str(task.id), job_id=f"plan-{task.id}")
    return PlanAccepted(
        task_id=task.id,
        job_id=job.id,
        status=task.status,
        plan_type=payload.plan_type,
    )


@router.get("/{task_id}")
def get_plan(task_id: str, db: Session = Depends(get_db)):
    task = db.get(Task, uuid.UUID(task_id))
    if task is None or task.agent != "planner":
        raise HTTPException(status_code=404, detail="Plan task not found")
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
