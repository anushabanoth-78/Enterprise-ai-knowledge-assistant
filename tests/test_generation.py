import uuid

from app.services.generation import build_messages, extract_citations
from app.services.retrieval import Passage


def test_extract_citations_flags_invented_sources():
    valid, invalid = extract_citations("Torque is 12 Nm [1][2]. Also see [9].", n_sources=3)
    assert valid == [1, 2] and invalid == [9]


def test_prompt_numbers_sources_with_page():
    p = Passage(1, uuid.uuid4(), "manual.pdf", 7, "Use 12 Nm.", 0.9)
    assert "[1] (manual.pdf, p.7)" in build_messages("torque?", [p])[1]["content"]
