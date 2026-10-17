from app.services.evaluation import keyword_recall


def test_keyword_recall():
    assert keyword_recall("The torque is 12 Nm", ["torque", "12 nm", "bolt"]) == 2 / 3
    assert keyword_recall("anything", []) == 1.0
