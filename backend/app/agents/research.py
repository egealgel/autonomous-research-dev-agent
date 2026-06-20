import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.agents.claude import ClaudeResult, run_task_with_system
from app.rag import SearchHit, search, store_chunks
from app.tools.github import fetch_repo, parse_repo_url
from app.tools.scrape import chunk_text, scrape

RESEARCH_SYSTEM_PROMPT = (
    "You are a research assistant. Use ONLY the provided CONTEXT excerpts to answer. "
    "If the context is insufficient, say so explicitly rather than guessing. "
    "Cite source URLs inline as [n] referencing the numbered context blocks. "
    "Produce a thorough, well-structured Markdown report."
)


@dataclass
class IngestedSource:
    url: str
    source_type: str
    title: str
    chunks_stored: int
    meta: dict = field(default_factory=dict)


def _ingest_github_repo(db: Session, task_id: uuid.UUID, url: str) -> IngestedSource:
    owner, name = parse_repo_url(url)
    repo = fetch_repo(owner, name)

    parts: list[str] = [
        f"# {owner}/{name}",
        f"Description: {repo.description or 'N/A'}",
        f"Language: {repo.language or 'N/A'}",
        f"Stars: {repo.stars} | Forks: {repo.forks} | Open issues: {repo.open_issues}",
        f"Topics: {', '.join(repo.topics) if repo.topics else 'N/A'}",
    ]
    if repo.readme_md:
        parts.append("\n## README\n")
        parts.append(repo.readme_md)

    full_text = "\n".join(parts)
    chunks = chunk_text(full_text)
    meta = {
        "owner": owner,
        "name": name,
        "stars": repo.stars,
        "language": repo.language,
        "default_branch": repo.default_branch,
    }
    store_chunks(
        db,
        task_id=task_id,
        source_url=url,
        source_type="github_repo",
        chunks=chunks,
        meta=meta,
    )
    return IngestedSource(
        url=url,
        source_type="github_repo",
        title=f"{owner}/{name}",
        chunks_stored=len(chunks),
        meta=meta,
    )


def _ingest_web(db: Session, task_id: uuid.UUID, url: str) -> IngestedSource:
    page = scrape(url)
    chunks = chunk_text(page.text)
    store_chunks(
        db,
        task_id=task_id,
        source_url=url,
        source_type="web",
        chunks=chunks,
        meta={"title": page.title},
    )
    return IngestedSource(
        url=url,
        source_type="web",
        title=page.title,
        chunks_stored=len(chunks),
    )


def ingest_url(db: Session, task_id: uuid.UUID, url: str) -> IngestedSource:
    if "github.com/" in url:
        return _ingest_github_repo(db, task_id, url)
    return _ingest_web(db, task_id, url)


def _build_context(hits: list[SearchHit]) -> str:
    blocks: list[str] = []
    for i, hit in enumerate(hits, start=1):
        blocks.append(
            f"[{i}] source={hit.source_url} (type={hit.source_type}, sim={hit.similarity:.3f})\n{hit.content}"
        )
    return "\n\n---\n\n".join(blocks)


@dataclass
class ResearchOutcome:
    sources: list[IngestedSource]
    hits: list[SearchHit]
    claude: ClaudeResult


def run_research(db: Session, task_id: uuid.UUID, prompt: str, urls: list[str]) -> ResearchOutcome:
    sources = [ingest_url(db, task_id, url) for url in urls]
    db.flush()

    hits = search(db, prompt, task_id=task_id, limit=8)
    context = _build_context(hits)
    user_message = f"CONTEXT:\n{context}\n\n---\nTASK:\n{prompt}"

    claude = run_task_with_system(user_message, system=RESEARCH_SYSTEM_PROMPT, max_tokens=4096)
    return ResearchOutcome(sources=sources, hits=hits, claude=claude)
