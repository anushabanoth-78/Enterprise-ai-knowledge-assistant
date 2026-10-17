"""Grounded answer generation. Retrieval is deliberately separate from this module."""
import re
import time
from dataclasses import dataclass

import httpx
import structlog
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.services.retrieval import Passage

log = structlog.get_logger()

SYSTEM_PROMPT = (
    "You answer questions using ONLY the numbered sources provided. "
    "Cite every claim with its source number in square brackets, e.g. [1] or [2][3]. "
    "If the sources do not contain the answer, say you could not find it in the documents. "
    "Never invent source numbers."
)


@dataclass
class Generation:
    answer: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float


def build_messages(question: str, passages: list[Passage]) -> list[dict]:
    context = "\n\n".join(f"[{i}] ({p.filename}, p.{p.page})\n{p.content}" for i, p in enumerate(passages, 1))
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Sources:\n{context}\n\nQuestion: {question}"},
    ]


def extract_citations(answer: str, n_sources: int) -> tuple[list[int], list[int]]:
    """Returns (valid refs, invalid refs) found in the answer text."""
    refs = {int(m) for m in re.findall(r"\[(\d+)\]", answer)}
    return sorted(r for r in refs if 1 <= r <= n_sources), sorted(r for r in refs if not 1 <= r <= n_sources)


def _retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return isinstance(exc, (httpx.TransportError, httpx.TimeoutException))


_retry = retry(retry=retry_if_exception(_retryable), stop=stop_after_attempt(3),
               wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)


@_retry
def _call_hosted(messages: list[dict]) -> tuple[str, str, int, int]:
    r = httpx.post(
        f"{settings.hosted_base_url}/chat/completions",
        headers={"Authorization": f"Bearer {settings.hosted_api_key}"},
        json={"model": settings.hosted_model, "messages": messages, "temperature": 0.1},
        timeout=settings.llm_timeout_s,
    )
    r.raise_for_status()
    data = r.json()
    usage = data.get("usage", {})
    return (data["choices"][0]["message"]["content"], settings.hosted_model,
            usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))


@_retry
def _call_ollama(messages: list[dict]) -> tuple[str, str, int, int]:
    r = httpx.post(
        f"{settings.ollama_url}/api/chat",
        json={"model": settings.ollama_model, "messages": messages, "stream": False,
              "options": {"temperature": 0.1}},
        timeout=settings.llm_timeout_s * 3,  # local models are slower
    )
    r.raise_for_status()
    data = r.json()
    return (data["message"]["content"], settings.ollama_model,
            data.get("prompt_eval_count", 0), data.get("eval_count", 0))


PROVIDERS = {"hosted": _call_hosted, "ollama": _call_ollama}


def generate(provider: str, question: str, passages: list[Passage]) -> Generation:
    if not passages:
        return Generation("I could not find anything relevant in your documents.", "none", 0, 0, 0.0)
    start = time.perf_counter()
    answer, model, pt, ct = PROVIDERS[provider](build_messages(question, passages))
    ms = (time.perf_counter() - start) * 1000
    log.info("generation_done", provider=provider, model=model, ms=round(ms), pt=pt, ct=ct)
    return Generation(answer, model, pt, ct, ms)
