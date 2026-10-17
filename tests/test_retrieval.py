from app.services.retrieval import reciprocal_rank_fusion


def test_rrf_rewards_agreement_between_rankers():
    scores = reciprocal_rank_fusion([[1, 2, 3], [3, 1, 4]])
    assert max(scores, key=scores.get) in (1, 3)
    assert scores[1] > scores[2] and scores[3] > scores[4]


def test_rrf_handles_empty_rankings():
    assert reciprocal_rank_fusion([[], []]) == {}
