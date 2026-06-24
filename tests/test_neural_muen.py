from __future__ import annotations

import math

import pandas as pd

from sisacao8.neural_muen import (
    GATE_ENGINE_VERSION,
    GateThresholds,
    MuenTrialKey,
    aggregate_family_evaluation,
    build_trial_id,
    evaluate_fold_economics,
    gate_decision_row,
    research_gate_decision,
)


def test_trial_id_is_stable_and_changes_with_seed() -> None:
    base = MuenTrialKey(
        protocol_version="neural_eod_protocol_v1",
        dataset_snapshot="snapshot_a",
        candidate_family_hash="family_a",
        fold_id="fold_01",
        seed=42,
        code_commit="abc123",
    )
    changed_seed = MuenTrialKey(
        protocol_version=base.protocol_version,
        dataset_snapshot=base.dataset_snapshot,
        candidate_family_hash=base.candidate_family_hash,
        fold_id=base.fold_id,
        seed=43,
        code_commit=base.code_commit,
    )

    assert build_trial_id(base) == build_trial_id(base)
    assert build_trial_id(base).startswith("trial_")
    assert build_trial_id(base) != build_trial_id(changed_seed)


def test_evaluate_fold_economics_uses_realized_buy_sell_returns() -> None:
    frame = pd.DataFrame(
        {
            "predicted_label": ["up", "down", "neutral", "up"],
            "buy_net_return": [0.04, -0.02, 0.01, -0.03],
            "sell_net_return": [-0.04, 0.05, -0.01, 0.02],
            "champion_net_return": [0.01, 0.01, 0.0, 0.01],
        }
    )

    metrics = evaluate_fold_economics(frame, fold_id="fold_01")

    assert metrics.fold_id == "fold_01"
    assert metrics.trades == 3
    assert metrics.coverage == 0.75
    assert metrics.expectancy_net == (0.04 + 0.05 - 0.03) / 3
    assert metrics.delta_expectancy_vs_champion == metrics.expectancy_net - 0.01
    assert metrics.profit_factor == (0.04 + 0.05) / 0.03
    assert metrics.max_drawdown > 0


def test_research_gate_rejects_before_score_when_core_evidence_is_missing() -> None:
    fold_metrics = [
        evaluate_fold_economics(
            pd.DataFrame(
                {
                    "predicted_label": ["up", "neutral"],
                    "buy_net_return": [0.01, 0.0],
                    "sell_net_return": [0.0, 0.0],
                    "champion_net_return": [0.02, 0.0],
                }
            ),
            fold_id="fold_01",
        )
    ]
    family = aggregate_family_evaluation("family_a", fold_metrics, seed_count=1)

    decision = research_gate_decision(family)

    assert not decision.passed
    assert decision.decision_status == "rejected"
    assert "trades_insuficientes" in decision.failed_criteria
    assert "stress_custo_ausente" in decision.failed_criteria


def test_research_gate_passes_stable_positive_family_with_cost_stress() -> None:
    fold_metrics = []
    for index in range(5):
        frame = pd.DataFrame(
            {
                "predicted_label": ["up"] * 10,
                "buy_net_return": [0.03 + index * 0.001] * 10,
                "sell_net_return": [0.0] * 10,
                "champion_net_return": [0.01] * 10,
            }
        )
        fold_metrics.append(
            evaluate_fold_economics(frame, fold_id=f"fold_{index + 1:02d}")
        )
        fold_metrics.append(
            evaluate_fold_economics(
                frame, fold_id=f"fold_{index + 1:02d}", cost_multiplier=1.5
            )
        )
    family = aggregate_family_evaluation("family_a", fold_metrics, seed_count=3)

    decision = research_gate_decision(family, GateThresholds(min_trades=30))

    assert decision.passed
    assert decision.failed_criteria == ()
    assert decision.metrics["positive_folds"] >= 5
    assert math.isclose(decision.metrics["median_delta_expectancy_vs_champion"], 0.022)


def test_gate_decision_row_is_bigquery_ready() -> None:
    fold_metrics = [
        evaluate_fold_economics(
            pd.DataFrame(
                {
                    "predicted_label": ["up"] * 10,
                    "buy_net_return": [0.03] * 10,
                    "sell_net_return": [0.0] * 10,
                    "champion_net_return": [0.01] * 10,
                }
            ),
            fold_id="fold_01",
            cost_multiplier=1.5,
        )
    ]
    family = aggregate_family_evaluation("family_a", fold_metrics, seed_count=3)
    decision = research_gate_decision(
        family,
        GateThresholds(min_trades=1, min_positive_folds=1),
    )

    row = gate_decision_row(
        protocol_version="neural_eod_protocol_v1",
        dataset_snapshot="snapshot_a",
        candidate_family_hash="family_a",
        decision=decision,
    )

    assert row["decision_id"].startswith("gate_")
    assert row["gate_engine_version"] == GATE_ENGINE_VERSION
    assert row["metrics_json"]["candidate_family_hash"] == "family_a"
    assert isinstance(row["failed_criteria"], list)
