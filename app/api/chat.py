import time

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import rate_limit
from app.db import repository
from app.db.models import User
from app.models.schemas import ChatIn, ChatOut, CitationOut
from app.services import evaluation, generation, retrieval

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatOut)
def chat(body: ChatIn, user: User = Depends(rate_limit), db: Session = Depends(repository.get_db)):
    t0 = time.perf_counter()
    passages = retrieval.retrieve(db, user.id, body.question, body.top_k, body.rerank, body.document_ids)
    retrieval_ms = (time.perf_counter() - t0) * 1000
    try:
        gen = generation.generate(body.provider, body.question, passages)
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"LLM provider failed: {exc.__class__.__name__}")

    valid, _ = generation.extract_citations(gen.answer, len(passages))
    repository.add_query_log(
        db, owner_id=user.id, question=body.question, provider=body.provider, model=gen.model,
        retrieval_ms=retrieval_ms, generation_ms=gen.latency_ms, prompt_tokens=gen.prompt_tokens,
        completion_tokens=gen.completion_tokens, n_citations=len(valid))
    return ChatOut(
        answer=gen.answer, provider=body.provider, model=gen.model,
        citations=[CitationOut(ref=i, document_id=p.document_id, filename=p.filename, page=p.page,
                               text=p.content, score=round(p.score, 4))
                   for i, p in enumerate(passages, 1)],
        retrieval_ms=round(retrieval_ms, 1), generation_ms=round(gen.latency_ms, 1),
        prompt_tokens=gen.prompt_tokens, completion_tokens=gen.completion_tokens)


@router.get("/evaluation/results")
def eval_results(user: User = Depends(rate_limit)):
    return evaluation.read_results()


@router.get("/evaluation/usage")
def eval_usage(user: User = Depends(rate_limit), db: Session = Depends(repository.get_db)):
    return repository.usage_stats(db, user.id)
