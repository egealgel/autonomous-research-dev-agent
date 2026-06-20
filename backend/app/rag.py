import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.embeddings import embed_text, embed_texts
from app.models import Document


@dataclass
class SearchHit:
    document_id: uuid.UUID
    source_url: str
    source_type: str
    chunk_index: int
    content: str
    similarity: float


def store_chunks(
    db: Session,
    *,
    task_id: uuid.UUID | None,
    source_url: str,
    source_type: str,
    chunks: list[str],
    meta: dict | None = None,
) -> list[Document]:
    if not chunks:
        return []
    embeddings = embed_texts(chunks)
    docs = [
        Document(
            task_id=task_id,
            source_url=source_url,
            source_type=source_type,
            chunk_index=i,
            content=chunk,
            embedding=embedding,
            meta=meta,
        )
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True))
    ]
    db.add_all(docs)
    db.flush()
    return docs


def search(
    db: Session,
    query: str,
    *,
    task_id: uuid.UUID | None = None,
    limit: int = 6,
) -> list[SearchHit]:
    query_vector = embed_text(query)
    distance = Document.embedding.cosine_distance(query_vector)

    stmt = select(Document, distance.label("distance")).order_by(distance).limit(limit)
    if task_id is not None:
        stmt = stmt.where(Document.task_id == task_id)

    rows = db.execute(stmt).all()
    return [
        SearchHit(
            document_id=doc.id,
            source_url=doc.source_url,
            source_type=doc.source_type,
            chunk_index=doc.chunk_index,
            content=doc.content,
            similarity=1.0 - float(dist),
        )
        for doc, dist in rows
    ]
