import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, HttpUrl, ValidationError
from sqlalchemy.orm import Session

from app.agents.planner import PlanType
from app.db import get_db
from app.jobs import process_plan_task
from app.models import Task, TaskStatus
from app.queue import plan_queue
from app.storage import storage, upload_key
from app.tools.image import ImageAttachment, validate_image
from app.tools.text_doc import TextDocument, validate_text_doc

router = APIRouter(prefix="/plan", tags=["plan"])


class _UrlList(BaseModel):
    urls: list[HttpUrl]


class PlanAccepted(BaseModel):
    task_id: uuid.UUID
    job_id: str
    status: str
    plan_type: PlanType


def _parse_urls(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return [line.strip() for line in raw.splitlines() if line.strip()]
    if not isinstance(loaded, list):
        raise HTTPException(status_code=422, detail="urls must be a JSON array of strings")
    try:
        validated = _UrlList(urls=loaded)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    return [str(u) for u in validated.urls]


@router.post("", response_model=PlanAccepted, status_code=202)
async def create_plan(
    prompt: str = Form(..., min_length=1, max_length=10_000),
    plan_type: PlanType = Form(PlanType.software_roadmap),
    urls: str | None = Form(None),
    images: list[UploadFile] = File(default_factory=list),
    texts: list[UploadFile] = File(default_factory=list),
    db: Session = Depends(get_db),
) -> PlanAccepted:
    url_list = _parse_urls(urls)

    image_attachments: list[ImageAttachment] = []
    for f in images:
        if not f or not f.filename:
            continue
        content = await f.read()
        try:
            image_attachments.append(
                validate_image(content, filename=f.filename, content_type=f.content_type)
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    text_docs: list[TextDocument] = []
    for f in texts:
        if not f or not f.filename:
            continue
        content = await f.read()
        try:
            text_docs.append(validate_text_doc(content, filename=f.filename))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    task = Task(
        prompt=prompt,
        agent="planner",
        status=TaskStatus.pending,
        params={
            "plan_type": plan_type.value,
            "urls": url_list,
            "attached_images": [],
            "attached_text_docs": [],
        },
        created_at=datetime.now(timezone.utc),
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    attached_images = []
    for img in image_attachments:
        key = upload_key(task.id, img.filename)
        storage.write_binary(key, img.data)
        attached_images.append(
            {
                "filename": img.filename,
                "media_type": img.media_type,
                "storage_key": key,
            }
        )

    attached_text_docs = []
    for doc in text_docs:
        key = upload_key(task.id, doc.filename)
        storage.write_binary(key, doc.content.encode("utf-8"))
        attached_text_docs.append(
            {
                "filename": doc.filename,
                "storage_key": key,
                "inline": doc.inline,
            }
        )

    task.params = {
        **(task.params or {}),
        "attached_images": attached_images,
        "attached_text_docs": attached_text_docs,
    }
    db.commit()

    job = plan_queue.enqueue(process_plan_task, str(task.id), job_id=f"plan-{task.id}")
    return PlanAccepted(
        task_id=task.id,
        job_id=job.id,
        status=task.status,
        plan_type=plan_type,
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


@router.get("/{task_id}/uploads/{filename}")
def get_upload(task_id: str, filename: str, db: Session = Depends(get_db)):
    from fastapi.responses import Response

    task = db.get(Task, uuid.UUID(task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    params = task.params or {}
    for ref in params.get("attached_images", []) or []:
        if ref["filename"] == filename:
            data = storage.read_binary(ref["storage_key"])
            return Response(content=data, media_type=ref["media_type"])
    for ref in params.get("attached_text_docs", []) or []:
        if ref["filename"] == filename:
            data = storage.read_binary(ref["storage_key"])
            return Response(content=data, media_type="text/plain; charset=utf-8")
    raise HTTPException(status_code=404, detail="Upload not found on this task")
