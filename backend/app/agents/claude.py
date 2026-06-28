from dataclasses import dataclass
from typing import Any

from anthropic import Anthropic

from app.config import settings
from app.pricing import cost_usd

SYSTEM_PROMPT = (
    "You are an autonomous research and development assistant. "
    "When given a task, produce a thorough, well-structured Markdown response. "
    "Cite reasoning. If asked to summarize a URL, work from your knowledge or ask for the content if missing."
)


def _get_client() -> Anthropic:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured. Set it in backend/.env")
    return Anthropic(api_key=settings.anthropic_api_key)


@dataclass
class ClaudeResult:
    text: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    cost_usd: float
    model: str
    raw: dict


def run_messages(
    *,
    system: str,
    content: str | list[dict[str, Any]],
    max_tokens: int = 4096,
) -> ClaudeResult:
    client = _get_client()
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": content}],
    )

    text_parts = [block.text for block in response.content if block.type == "text"]
    text = "\n".join(text_parts)

    usage = response.usage
    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens
    cache_creation = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0

    return ClaudeResult(
        text=text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_tokens=cache_creation,
        cache_read_tokens=cache_read,
        cost_usd=cost_usd(
            settings.anthropic_model,
            input_tokens,
            output_tokens,
            cache_creation,
            cache_read,
        ),
        model=settings.anthropic_model,
        raw=response.model_dump(mode="json"),
    )


def run_task_with_system(prompt: str, *, system: str, max_tokens: int = 4096) -> ClaudeResult:
    return run_messages(system=system, content=prompt, max_tokens=max_tokens)


def run_task(prompt: str, *, max_tokens: int = 4096) -> ClaudeResult:
    return run_messages(system=SYSTEM_PROMPT, content=prompt, max_tokens=max_tokens)
