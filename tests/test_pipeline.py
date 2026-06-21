"""End-to-end pipeline tests. Research only. Not financial advice."""

from __future__ import annotations

from opportunity_engine.models import DISCLAIMER


def test_scan_produces_ranked_opportunities(scan_result):
    opps = scan_result.opportunities
    assert len(opps) > 0
    # Ranks are 1..N contiguous and sorted by descending final score.
    assert [o.rank for o in opps] == list(range(1, len(opps) + 1))
    scores = [o.scores.final_score for o in opps]
    assert scores == sorted(scores, reverse=True)


def test_every_opportunity_has_a_catalyst(scan_result):
    for o in scan_result.opportunities:
        assert len(o.catalyst.catalysts) >= 1


def test_every_opportunity_complete(scan_result):
    for o in scan_result.top:
        assert o.company
        assert o.current_price > 0
        assert o.thesis.summary
        assert o.thesis.bull_case and o.thesis.bear_case and o.thesis.base_case
        assert o.thesis.key_risks
        assert o.plan.target_1 > 0
        assert o.disclaimer == DISCLAIMER


def test_to_dict_is_json_serializable(scan_result):
    import json

    d = scan_result.opportunities[0].to_dict()
    json.dumps(d)  # must not raise
    assert d["disclaimer"] == DISCLAIMER
    assert d["risk"]["level"] in {"Low", "Medium", "High", "Speculative"}


def test_deterministic_scan(settings):
    from opportunity_engine.engine.pipeline import run_scan

    a = run_scan(settings)
    b = run_scan(settings)
    assert [o.ticker for o in a.opportunities] == [o.ticker for o in b.opportunities]
    assert [o.scores.final_score for o in a.opportunities] == \
           [o.scores.final_score for o in b.opportunities]
