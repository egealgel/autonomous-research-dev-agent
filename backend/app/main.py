from fastapi import FastAPI

from app.routes import plan, research, tasks, usage

app = FastAPI(title="Autonomous Research & Dev Agent", version="0.3.0")

app.include_router(tasks.router)
app.include_router(usage.router)
app.include_router(research.router)
app.include_router(plan.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
