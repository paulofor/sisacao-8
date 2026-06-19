import datetime as dt

import pytest

from sisacao8.neural_paper_trading import (
    NeuralPaperTradingCriteria,
    build_neural_paper_orders,
    evaluate_neural_backtest_for_paper,
)


def test_evaluate_neural_backtest_approves_minimum_viable_metrics():
    decision = evaluate_neural_backtest_for_paper(
        {
            "profit_factor": 1.21,
            "win_rate": 0.56,
            "fill_rate": 0.62,
            "max_drawdown_pct": 0.08,
            "trade_count": 80,
            "avg_return_pct": 0.015,
            "cost_sensitivity_pct": 0.10,
        }
    )

    assert decision.approved is True
    assert decision.status == "approved_for_paper"
    assert decision.failed_criteria == ()


def test_evaluate_neural_backtest_blocks_weak_metrics_with_reasons():
    decision = evaluate_neural_backtest_for_paper(
        {
            "profit_factor": 1.0,
            "win_rate": 0.49,
            "fill_rate": 0.30,
            "max_drawdown_pct": 0.20,
            "trade_count": 12,
            "avg_return_pct": -0.01,
            "cost_sensitivity_pct": 0.40,
        },
        NeuralPaperTradingCriteria(min_trades=20),
    )

    assert decision.approved is False
    assert decision.status == "blocked_for_paper"
    assert set(decision.failed_criteria) == {
        "profit_factor",
        "win_rate",
        "fill_rate",
        "max_drawdown_pct",
        "trade_count",
        "avg_return_pct",
        "cost_sensitivity_pct",
    }


def test_build_neural_paper_orders_limits_and_applies_slippage():
    created_at = dt.datetime(2026, 6, 19, 21, 0, tzinfo=dt.timezone.utc)
    orders = build_neural_paper_orders(
        [
            {
                "date_ref": "2026-06-18",
                "valid_for": "2026-06-19",
                "ticker": "petr4",
                "side": "BUY",
                "entry": 10.0,
                "rank": 2,
                "score": 0.8,
                "model_version": "neural:v1",
            },
            {
                "date_ref": "2026-06-18",
                "valid_for": "2026-06-19",
                "ticker": "vale3",
                "side": "SELL",
                "entry": 20.0,
                "rank": 1,
                "score": 0.7,
                "model_version": "neural:v1",
            },
        ],
        run_id="run-1",
        quantity=10,
        slippage_pct=0.01,
        max_orders=1,
        created_at=created_at,
    )

    assert len(orders) == 1
    assert orders[0]["ticker"] == "VALE3"
    assert orders[0]["simulated_entry_price"] == pytest.approx(19.8)
    assert orders[0]["notional_brl"] == pytest.approx(198.0)
    assert orders[0]["order_status"] == "aberta"
    assert orders[0]["created_at"] == created_at
