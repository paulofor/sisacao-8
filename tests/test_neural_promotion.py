import datetime as dt

import pytest

from sisacao8.neural_promotion import (
    NeuralPromotionCriteria,
    build_promotion_audit_record,
    evaluate_neural_promotion,
    latest_controlled_promotion,
)


def test_evaluate_neural_promotion_requires_metrics_and_explicit_approval():
    decision = evaluate_neural_promotion(
        {
            "oos_profit_factor": 1.20,
            "oos_win_rate": 0.55,
            "paper_profit_factor": 1.18,
            "paper_win_rate": 0.53,
            "paper_days": 130,
            "paper_trades": 80,
            "paper_max_drawdown_pct": 0.08,
            "fill_rate": 0.61,
            "avg_abs_backtest_divergence_pct": 0.02,
        },
        explicit_approvals=("risk-owner",),
        evaluated_at=dt.datetime(2026, 6, 19, 22, 0, tzinfo=dt.timezone.utc),
    )

    assert decision.approved is True
    assert decision.status == "approved_for_controlled_promotion"
    assert decision.failed_criteria == ()
    assert decision.effective_signal_source == "hybrid"
    assert decision.fallback_signal_source == "heuristic"


def test_evaluate_neural_promotion_blocks_without_approval_or_enough_paper_days():
    decision = evaluate_neural_promotion(
        {
            "oos_profit_factor": 1.20,
            "oos_win_rate": 0.55,
            "paper_profit_factor": 1.18,
            "paper_win_rate": 0.53,
            "paper_days": 40,
            "paper_trades": 20,
            "paper_max_drawdown_pct": 0.16,
            "fill_rate": 0.20,
            "avg_abs_backtest_divergence_pct": 0.10,
        },
        criteria=NeuralPromotionCriteria(min_paper_days=60, min_paper_trades=30),
    )

    assert decision.approved is False
    assert decision.status == "blocked_for_promotion"
    assert set(decision.failed_criteria) == {
        "paper_days",
        "paper_trades",
        "paper_max_drawdown_pct",
        "fill_rate",
        "avg_abs_backtest_divergence_pct",
        "explicit_approval",
    }
    assert decision.effective_signal_source == "heuristic"


def test_build_promotion_audit_record_and_select_latest_approved():
    evaluated_at = dt.datetime(2026, 6, 19, 22, 0, tzinfo=dt.timezone.utc)
    decision = evaluate_neural_promotion(
        {
            "oos_profit_factor": 1.20,
            "oos_win_rate": 0.55,
            "paper_profit_factor": 1.18,
            "paper_win_rate": 0.53,
            "paper_days": 130,
            "paper_trades": 80,
            "paper_max_drawdown_pct": 0.08,
            "fill_rate": 0.61,
            "avg_abs_backtest_divergence_pct": 0.02,
        },
        explicit_approvals=("risk-owner",),
        evaluated_at=evaluated_at,
    )

    record = build_promotion_audit_record(
        model_id="neural_eod_mlp",
        model_version="v1",
        decision=decision,
        requested_by="codex",
        approval_ticket="MANUAL-1",
    )

    assert record["promotion_date"] == dt.date(2026, 6, 19)
    assert record["effective_signal_source"] == "hybrid"
    assert record["fallback_signal_source"] == "heuristic"
    assert record["approval_ticket"] == "MANUAL-1"
    assert latest_controlled_promotion([record])["model_version"] == "v1"


def test_latest_controlled_promotion_requires_audit_columns():
    with pytest.raises(KeyError):
        latest_controlled_promotion(
            [{"promotion_status": "approved_for_controlled_promotion"}]
        )
