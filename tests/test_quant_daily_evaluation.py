import datetime as dt

from functions.quant_daily_evaluation import main as quant_eval


def test_evaluate_ranking_row_blocks_when_no_monotonicity():
    result = quant_eval.evaluate_ranking_row(
        {
            "ranking_model_id": "asset_ranking_simple_v1",
            "ranking_model_version": "v1",
            "top_n": 3,
            "portfolio_days": 66,
            "positive_day_rate": 0.36,
            "avg_excess_vs_random_5d": -0.007,
            "decile_return_correlation": -0.1,
            "top_minus_bottom_decile_return_5d": -0.005,
            "ranking_status": "sem_monotonicidade",
        },
        dt.date(2026, 6, 16),
    )

    assert result.decision == "blocked"
    assert result.status == "sem_monotonicidade"
    assert "sem_monotonicidade" in result.reasons
    assert result.score < quant_eval.PAPER_THRESHOLD


def test_evaluate_ranking_row_approves_candidate_when_strong():
    result = quant_eval.evaluate_ranking_row(
        {
            "ranking_model_id": "asset_ranking_simple_v2",
            "ranking_model_version": "v2",
            "top_n": 5,
            "portfolio_days": 90,
            "positive_day_rate": 0.72,
            "avg_excess_vs_random_5d": 0.014,
            "decile_return_correlation": 0.42,
            "top_minus_bottom_decile_return_5d": 0.031,
            "ranking_status": "monotonicidade_promissora",
        },
        dt.date(2026, 6, 16),
    )

    assert result.decision == "approved_candidate"
    assert result.score >= quant_eval.PROMOTE_THRESHOLD
    assert result.reasons == ["ranking_aprovado_pelos_criterios_diarios"]


def test_evaluate_robustness_row_keeps_alerts_as_reasons():
    result = quant_eval.evaluate_robustness_row(
        {
            "strategy_id": "mean_reversion_v1",
            "strategy_version": "phase2_baseline",
            "strategy_family": "mean_reversion",
            "robustness_score": 42.0,
            "oos_status": "degradado_oos",
            "overfitting_alerts": (
                "walk_forward_instavel,nao_supera_benchmark_aleatorio"
            ),
        },
        dt.date(2026, 6, 16),
    )

    assert result.decision == "blocked"
    assert result.reasons == [
        "walk_forward_instavel",
        "nao_supera_benchmark_aleatorio",
    ]


def test_evaluation_result_serializes_json_fields():
    result = quant_eval.EvaluationResult(
        reference_date=dt.date(2026, 6, 16),
        evaluation_type="ranking",
        subject_id="model",
        subject_version="v1",
        score=80.12345,
        decision="approved_candidate",
        status="ok",
        reasons=["bom"],
        metrics={"positive_day_rate": 0.7},
    )

    row = result.to_bq_row(
        evaluated_at=dt.datetime(2026, 6, 16, tzinfo=dt.timezone.utc),
        run_id="abc",
    )

    assert row["readiness_score"] == 80.1235
    assert row["reasons_json"] == '["bom"]'
    assert '"positive_day_rate": 0.7' in row["metrics_json"]
