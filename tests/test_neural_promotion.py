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


def test_evaluate_neural_shadow_candidate_allows_only_shadow_status():
    from sisacao8.neural_promotion import evaluate_neural_shadow_candidate

    decision = evaluate_neural_shadow_candidate(
        {
            "train": {"accuracy": 0.46},
            "validation": {
                "accuracy": 0.39,
                "directional_precision": 0.36,
                "coverage": 0.37,
            },
            "test": {
                "rows_count": 750,
                "accuracy": 0.424,
                "directional_precision": 0.348,
                "coverage": 0.364,
            },
        },
        evaluated_at=dt.datetime(2026, 6, 21, 1, 30, tzinfo=dt.timezone.utc),
    )

    assert decision.approved is True
    assert decision.status == "shadow_candidate"
    assert decision.failed_criteria == ()
    assert decision.metrics["test_rows"] == 750


def test_evaluate_neural_shadow_candidate_blocks_weak_oos_and_alerts():
    from sisacao8.neural_promotion import evaluate_neural_shadow_candidate

    decision = evaluate_neural_shadow_candidate(
        {
            "train": {"accuracy": 0.75},
            "validation": {
                "accuracy": 0.55,
                "directional_precision": 0.50,
                "coverage": 0.50,
            },
            "test": {
                "rows_count": 200,
                "accuracy": 0.31,
                "directional_precision": 0.20,
                "coverage": 0.12,
            },
            "label_distribution_train": {"up": 0.30, "neutral": 0.40, "down": 0.30},
            "label_distribution_test": {"up": 0.55, "neutral": 0.25, "down": 0.20},
        }
    )

    assert decision.approved is False
    assert decision.status == "blocked_for_shadow"
    assert set(decision.failed_criteria) >= {
        "test_rows",
        "test_accuracy",
        "test_directional_precision",
        "test_coverage",
        "train_test_accuracy_gap",
        "validation_test_precision_gap",
        "label_drift_pct",
    }
    assert set(decision.alerts) == {
        "overfit_watch",
        "coverage_drop_watch",
        "label_drift_watch",
    }


def test_build_shadow_gate_audit_record():
    from sisacao8.neural_promotion import (
        build_shadow_gate_audit_record,
        evaluate_neural_shadow_candidate,
    )

    evaluated_at = dt.datetime(2026, 6, 21, 1, 30, tzinfo=dt.timezone.utc)
    decision = evaluate_neural_shadow_candidate(
        {
            "train": {"accuracy": 0.46},
            "validation": {"directional_precision": 0.36, "coverage": 0.37},
            "test": {
                "rows_count": 750,
                "accuracy": 0.424,
                "directional_precision": 0.348,
                "coverage": 0.364,
            },
        },
        evaluated_at=evaluated_at,
    )

    record = build_shadow_gate_audit_record(
        model_id="neural_eod_mlp",
        model_version="v-shadow",
        decision=decision,
        requested_by="codex",
        notes="fase 4",
    )

    assert record["decision_date"] == dt.date(2026, 6, 21)
    assert record["decision_status"] == "shadow_candidate"
    assert record["requested_by"] == "codex"
    assert record["notes"] == "fase 4"
