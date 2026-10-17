import uuid
from collections.abc import Iterator

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, joinedload, sessionmaker

from app.core.config import settings
from app.db.models import Base, Chunk, Document, QueryLog, User

engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=10, max_overflow=10)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)


# ---- users ----
def create_user(db: Session, email: str, password_hash: str) -> User:
    user = User(email=email.lower(), password_hash=password_hash)
    db.add(user)
    db.commit()
    return user


def get_user(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


# ---- documents (every read is scoped by owner_id) ----
def create_document(db: Session, owner_id: uuid.UUID, filename: str, path: str) -> Document:
    doc = Document(owner_id=owner_id, filename=filename, path=path)
    db.add(doc)
    db.commit()
    return doc


def get_document(db: Session, owner_id: uuid.UUID, doc_id: uuid.UUID) -> Document | None:
    return db.scalar(select(Document).where(Document.id == doc_id, Document.owner_id == owner_id))


def list_documents(db: Session, owner_id: uuid.UUID) -> list[Document]:
    return list(db.scalars(select(Document).where(Document.owner_id == owner_id).order_by(Document.created_at.desc())))


def delete_document(db: Session, doc: Document) -> None:
    db.delete(doc)
    db.commit()


# ---- retrieval primitives: ownership is enforced in the SQL itself ----
def vector_search(db: Session, owner_id: uuid.UUID, embedding: list[float], k: int,
                  document_ids: list[uuid.UUID] | None = None) -> list[tuple[Chunk, float]]:
    dist = Chunk.embedding.cosine_distance(embedding).label("dist")
    stmt = select(Chunk, dist).options(joinedload(Chunk.document)).where(Chunk.owner_id == owner_id)
    if document_ids:
        stmt = stmt.where(Chunk.document_id.in_(document_ids))
    rows = db.execute(stmt.order_by(dist).limit(k)).all()
    return [(c, 1.0 - d) for c, d in rows]


def keyword_search(db: Session, owner_id: uuid.UUID, query: str, k: int,
                   document_ids: list[uuid.UUID] | None = None) -> list[tuple[Chunk, float]]:
    tsq = func.websearch_to_tsquery("english", query)
    rank = func.ts_rank_cd(Chunk.tsv, tsq).label("rank")
    stmt = (select(Chunk, rank).options(joinedload(Chunk.document))
            .where(Chunk.owner_id == owner_id, Chunk.tsv.op("@@")(tsq)))
    if document_ids:
        stmt = stmt.where(Chunk.document_id.in_(document_ids))
    return [(c, float(r)) for c, r in db.execute(stmt.order_by(rank.desc()).limit(k)).all()]


# ---- query logs ----
def add_query_log(db: Session, **kw) -> None:
    db.add(QueryLog(**kw))
    db.commit()


def usage_stats(db: Session, owner_id: uuid.UUID) -> list[dict]:
    stmt = (select(QueryLog.provider, QueryLog.model, func.count(), func.avg(QueryLog.retrieval_ms),
                   func.avg(QueryLog.generation_ms), func.sum(QueryLog.prompt_tokens),
                   func.sum(QueryLog.completion_tokens))
            .where(QueryLog.owner_id == owner_id).group_by(QueryLog.provider, QueryLog.model))
    return [dict(provider=p, model=m, queries=n, avg_retrieval_ms=round(r or 0, 1),
                 avg_generation_ms=round(g or 0, 1), prompt_tokens=int(pt or 0),
                 completion_tokens=int(ct or 0))
            for p, m, n, r, g, pt, ct in db.execute(stmt).all()]
