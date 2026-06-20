import uuid
from datetime import datetime, timezone

from app.agents.research import run_research
from app.db import SessionLocal
from app.models import Task, TaskStatus, UsageLog
from app.storage import new_artifact_key, storage


def process_research_task(task_id: str) -> None:
    db = SessionLocal()
    try:
        task = db.get(Task, uuid.UUID(task_id))
        if task is None:
            raise RuntimeError(f"Task not found: {task_id}")

        task.status = TaskStatus.running
        db.commit()

        params = task.params or {}
        urls: list[str] = params.get("urls", [])

        try:
            outcome = run_research(db, task.id, task.prompt, urls)
        except Exception as exc:
            task.status = TaskStatus.failed
            task.error = f"{type(exc).__name__}: {exc}"
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
            raise

        artifact_key = new_artifact_key(task.id)
        path = storage.write_text(artifact_key, outcome.claude.text)

        task.result_text = outcome.claude.text
        task.result_path = path
        task.status = TaskStatus.succeeded
        task.completed_at = datetime.now(timezone.utc)
        task.params = {
            **(task.params or {}),
            "sources": [
                {
                    "url": s.url,
                    "type": s.source_type,
                    "title": s.title,
                    "chunks_stored": s.chunks_stored,
                }
                for s in outcome.sources
            ],
            "hits_used": [
                {"url": h.source_url, "chunk_index": h.chunk_index, "similarity": h.similarity}
                for h in outcome.hits
            ],
        }

        db.add(
            UsageLog(
                task_id=task.id,
                model=outcome.claude.model,
                input_tokens=outcome.claude.input_tokens,
                output_tokens=outcome.claude.output_tokens,
                cache_creation_tokens=outcome.claude.cache_creation_tokens,
                cache_read_tokens=outcome.claude.cache_read_tokens,
                cost_usd=outcome.claude.cost_usd,
                raw=outcome.claude.raw,
            )
        )
        db.commit()
    finally:
        db.close()
