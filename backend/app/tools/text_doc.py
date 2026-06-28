from dataclasses import dataclass

from app.tools.scrape import chunk_text

INLINE_MAX_CHARS = 8_000
MAX_DOC_BYTES = 2 * 1024 * 1024


@dataclass
class TextDocument:
    filename: str
    content: str
    inline: bool


def validate_text_doc(content: bytes, *, filename: str) -> TextDocument:
    if len(content) == 0:
        raise ValueError(f"Empty text file: {filename}")
    if len(content) > MAX_DOC_BYTES:
        raise ValueError(
            f"Text file '{filename}' is {len(content) // 1024} KB, max is {MAX_DOC_BYTES // 1024} KB"
        )
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Text file '{filename}' must be UTF-8 encoded") from exc

    return TextDocument(
        filename=filename,
        content=text,
        inline=len(text) <= INLINE_MAX_CHARS,
    )


def doc_chunks(doc: TextDocument) -> list[str]:
    return chunk_text(doc.content)
