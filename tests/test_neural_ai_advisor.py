import json

import pytest

from sisacao8.neural_ai_advisor import (
    build_advisor_audit,
    build_advisor_prompt,
    candidates_from_advisor_response,
    compare_advisor_against_control,
    parse_advisor_response,
)
from sisacao8.neural_evolution import EvolutionBudget


def _valid_response():
    return {
        "rationale": "Explorar menor dropout e pesos balanceados.",
        "candidates": [
            {
                "architecture": {
                    "type": "mlp",
                    "hidden_units": [128, 64],
                    "batch_norm": False,
                },
                "hyperparameters": {
                    "dropout_rate": 0.1,
                    "learning_rate": 0.0005,
                    "batch_size": 256,
                    "epochs": 40,
                    "class_weight": "balanced",
                },
                "risk_notes": ["validar estabilidade"],
            }
        ],
    }


def test_build_prompt_exposes_only_summary_budget_and_schema():
    prompt = build_advisor_prompt(
        leaderboard=[{"model_version": "v1", "score_total": 0.32}],
        budget=EvolutionBudget(max_trials=2),
        rejected_reasons=["directional_precision_test_below_baseline"],
    )

    assert prompt["task"] == "propose_neural_eod_candidate_configs"
    assert prompt["budget"]["max_trials"] == 2
    assert "expected_response_schema" in prompt
    assert "credentials" not in json.dumps(prompt).lower()


def test_parse_and_validate_advisor_response_accepts_structured_json():
    response = parse_advisor_response(json.dumps(_valid_response()))
    candidates, rejections = candidates_from_advisor_response(
        response,
        evolution_run_id="advisor-run",
        dataset_snapshot="snapshot-1",
        budget=EvolutionBudget(max_trials=2),
        model_version_prefix="advisor_test",
    )

    assert rejections == []
    assert len(candidates) == 1
    assert candidates[0].candidate_source == "gemini"
    assert candidates[0].training_request["class_weight"] == "balanced"
    assert candidates[0].training_request["early_stopping"] is True


def test_validate_advisor_response_rejects_out_of_budget_candidate():
    response = _valid_response()
    response["candidates"][0]["architecture"]["hidden_units"] = [512, 256, 128]

    candidates, rejections = candidates_from_advisor_response(
        response,
        evolution_run_id="advisor-run",
        dataset_snapshot="snapshot-1",
        budget=EvolutionBudget(max_trials=2, max_parameter_count=1000),
    )

    assert candidates == []
    assert any("max_parameter_count_exceeded" in reason for reason in rejections)


def test_build_advisor_audit_records_validation_status_and_counts():
    audit = build_advisor_audit(
        advisor_run_id="advisor-1",
        evolution_run_id="evo-1",
        model_name="gemini-1.5-pro",
        prompt_json={"task": "x"},
        response_json=_valid_response(),
        accepted_count=1,
        rejection_reasons=["candidate_2:duplicate_candidate"],
    )

    assert audit.validation_status == "accepted"
    assert audit.accepted_count == 1
    assert audit.rejected_count == 1


def test_compare_advisor_against_control_reports_ab_result():
    comparison = compare_advisor_against_control(
        advisor_scores=[0.36, 0.31],
        control_scores=[0.34],
    )

    assert comparison.advisor_won is True
    assert comparison.summary == "advisor_outperformed_control"


@pytest.mark.parametrize("payload", [[], {"rationale": 1, "candidates": []}])
def test_parse_advisor_response_rejects_invalid_shape(payload):
    with pytest.raises(ValueError):
        parse_advisor_response(json.dumps(payload))
