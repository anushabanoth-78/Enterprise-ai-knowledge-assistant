"""Extract text -> chunk -> embed -> index."""
import functools
import uuid

import fitz  # PyMuPDF
import structlog

from app.core.config import settings

log = structlog.get_logger()


def extract_pages(path: str) -> list[tuple[int, str]]:
    with fitz.open(path) as pdf:
        return [(i + 1, page.get_text()) for i, page in enumerate(pdf)]


def chunk_pages(pages: list[tuple[int, str]], size: int, overlap: int) -> list[tuple[int, str]]:
    """Sliding word window per page so every chunk keeps an exact page number for citations."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than chunk size")
    out: list[tuple[int, str]] = []
    step = size - overlap
    for page_no, text in pages:
        words = text.split()
        for start in range(0, len(words), step):
            out.append((page_no, " ".join(words[start:start + size])))
            if start + size >= len(words):
                break
    return out


@functools.lru_cache(maxsize=1)
def _embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(settings.embedding_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    vecs = _embedder().encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
    return vecs.tolist()


def process_document(doc_id: uuid.UUID) -> None:
    from app.db.models import Chunk, Document
    from app.db.repository import SessionLocal

    with SessionLocal() as db:
        doc = db.get(Document, doc_id)
        if doc is None:
            return
        doc.status, doc.error = "processing", None
        db.query(Chunk).filter(Chunk.document_id == doc.id).delete()
        db.commit()
        try:
            pages = extract_pages(doc.path)
            chunks = chunk_pages(pages, settings.chunk_words, settings.chunk_overlap)
            if not chunks:
                raise ValueError("No extractable text (scanned PDF? add OCR)")
            vectors = embed_texts([c for _, c in chunks])
            db.add_all([
                Chunk(document_id=doc.id, owner_id=doc.owner_id, page=p, idx=i, content=t, embedding=v)
                for i, ((p, t), v) in enumerate(zip(chunks, vectors))
            ])
            doc.n_pages, doc.n_chunks, doc.status = len(pages), len(chunks), "ready"
            db.commit()
            log.info("ingestion_done", document_id=str(doc.id), chunks=len(chunks))
        except Exception as exc:
            db.rollback()
            doc = db.get(Document, doc_id)
            doc.status, doc.error = "failed", str(exc)[:500]
            db.commit()
            log.error("ingestion_failed", document_id=str(doc_id), error=str(exc))
            raise
