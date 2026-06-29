from __future__ import annotations

import json

import functions.neural_evolution_orchestrator.main as module


class _FakeQueryJob:
    def __init__(self, rows):
        self._rows = rows

    def result(self):
        return list(self._rows)


class _FakeLoadJob:
    def result(self):
        return None


class _FakeClient:
    def __init__(self):
        self.loaded = []
        self.queries = []
        self.registry_by_version = {}
        self.leaderboard_rows = []

    def query(self, query, job_config=None):
        self.queries.append((query, job_config))
        if "GROUP BY dataset_snapshot" in query:
            return _FakeQueryJob([{"dataset_snapshot": "snapshot_2026"}])
        if "ANY_VALUE(feature_version)" in query:
            return _FakeQueryJob([{"value": "feature_eod_tabular_v1"}])
        if "ANY_VALUE(label_version)" in query:
            return _FakeQueryJob([{"value": "label_eod_barrier_v2"}])
        if "SELECT dedupe_hash" in query:
            return _FakeQueryJob([])
        if (
            "FROM `ingestaokraken.cotacao_intraday.vw_neural_evolution_leaderboard`"
            in query
        ):
            return _FakeQueryJob(self.leaderboard_rows)
        if "FROM `ingestaokraken.cotacao_intraday.neural_model_registry`" in query:
            return _FakeQueryJob([next(iter(self.registry_by_version.values()))])
        if query.strip().startswith("UPDATE"):
            return _FakeQueryJob([])
        raise AssertionError(query)

    def load_table_from_json(self, rows, table_id, job_config=None):
        self.loaded.append((table_id, list(rows)))
        return _FakeLoadJob()


class _Request:
    def __init__(self, body):
        self._body = body

    def get_json(self, silent=True):
        return self._body


def test_orchestrator_generates_trains_scores_and_persists(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(module, "_BQ_CLIENT", fake_client)

    def fake_invoke_training(payload):
        fake_client.registry_by_version[payload["model_version"]] = {
            "model_version": payload["model_version"],
            "metrics_json": {
                "train": {"accuracy": 0.50},
                "validation": {"accuracy": 0.46, "directional_precision": 0.42},
                "test": {
                    "accuracy": 0.44,
                    "coverage": 0.35,
                    "directional_precision": 0.43,
                },
            },
        }
        return {"status": "ok", "model_version": payload["model_version"]}

    monkeypatch.setattr(module, "_invoke_training", fake_invoke_training)

    response, status = module.neural_evolution_orchestrator(
        _Request(
            {
                "evolution_run_id": "run-test",
                "model_version_prefix": "evo_test",
                "budget": {"max_trials": 2, "random_seed": 42},
            }
        )
    )

    assert status == 200
    assert response["candidate_count"] == 2
    assert response["trained_count"] == 2
    assert response["evaluated_count"] == 2
    latest_snapshot_query = fake_client.queries[0][0]
    assert "COUNTIF(dataset_split = 'validation') > 0" in latest_snapshot_query
    assert "COUNTIF(dataset_split = 'test') > 0" in latest_snapshot_query
    loaded_tables = [table for table, _rows in fake_client.loaded]
    assert "ingestaokraken.cotacao_intraday.neural_evolution_runs" in loaded_tables
    assert "ingestaokraken.cotacao_intraday.neural_candidate_configs" in loaded_tables
    assert (
        "ingestaokraken.cotacao_intraday.neural_candidate_evaluations" in loaded_tables
    )
    assert "ingestaokraken.cotacao_intraday.neural_gate_decisions" in loaded_tables
    evaluation_rows = next(
        rows
        for table, rows in fake_client.loaded
        if table == "ingestaokraken.cotacao_intraday.neural_candidate_evaluations"
    )
    gate_rows = next(
        rows
        for table, rows in fake_client.loaded
        if table == "ingestaokraken.cotacao_intraday.neural_gate_decisions"
    )
    assert evaluation_rows[0]["decision"] in {"keep_candidate", "shadow_candidate"}
    assert evaluation_rows[0]["score_total"] > 0
    assert gate_rows[0]["decision_status"] == "blocked"
    assert gate_rows[0]["failed_criteria"] == ["muen_economics_missing"]
    assert response["gate_decision_count"] == 2


def test_orchestrator_phase2_uses_kept_leaderboard_candidates(monkeypatch):
    fake_client = _FakeClient()
    fake_client.leaderboard_rows = [
        {
            "candidate_id": "parent-1",
            "evolution_run_id": "run-phase1",
            "model_version": "neural_eod_mlp_evo1_01",
            "model_id": "neural_eod_mlp",
            "candidate_source": "deterministic",
            "architecture_json": {
                "type": "mlp",
                "hidden_units": [128, 64],
                "batch_norm": False,
            },
            "hyperparameters_json": {
                "dropout_rate": 0.15,
                "learning_rate": 0.001,
                "batch_size": 256,
                "epochs": 40,
                "random_seed": 20260621,
                "early_stopping": True,
                "early_stopping_patience": 8,
                "class_weight": "balanced",
            },
            "score_total": 0.42,
            "score_directional_precision": 0.35,
            "score_coverage": 0.30,
            "score_generalization": 0.10,
            "score_stability": 0.10,
            "score_cost_penalty": 0.01,
            "decision": "keep_candidate",
            "decision_reasons_json": [],
        }
    ]
    monkeypatch.setattr(module, "_BQ_CLIENT", fake_client)

    def fake_invoke_training(payload):
        fake_client.registry_by_version[payload["model_version"]] = {
            "model_version": payload["model_version"],
            "metrics_json": {
                "train": {"accuracy": 0.50},
                "validation": {"accuracy": 0.46, "directional_precision": 0.42},
                "test": {
                    "accuracy": 0.44,
                    "coverage": 0.35,
                    "directional_precision": 0.43,
                },
            },
        }
        return {"status": "ok", "model_version": payload["model_version"]}

    monkeypatch.setattr(module, "_invoke_training", fake_invoke_training)

    response, status = module.neural_evolution_orchestrator(
        _Request(
            {
                "evolution_run_id": "run-phase2",
                "strategy": "deterministic_phase2",
                "model_version_prefix": "evo2_test",
                "budget": {"max_trials": 1, "random_seed": 42},
            }
        )
    )

    assert status == 200
    assert response["candidate_count"] == 1
    assert response["candidates"] == ["evo2_test_mutation_01"]
    config_rows = next(
        rows
        for table, rows in fake_client.loaded
        if table == "ingestaokraken.cotacao_intraday.neural_candidate_configs"
    )
    assert config_rows[0]["candidate_source"] == "mutation"
    assert config_rows[0]["training_request_json"]["early_stopping"] is True


def test_orchestrator_phase2_consolidates_similar_parent_families(monkeypatch):
    fake_client = _FakeClient()
    base_parent = {
        "candidate_id": "parent-1",
        "evolution_run_id": "run-phase1",
        "model_version": "neural_eod_mlp_evo1_01",
        "model_id": "neural_eod_mlp",
        "candidate_source": "deterministic",
        "architecture_json": {
            "type": "mlp",
            "hidden_units": [128, 64],
            "batch_norm": False,
        },
        "hyperparameters_json": {
            "dropout_rate": 0.15,
            "learning_rate": 0.001,
            "batch_size": 256,
            "epochs": 40,
            "random_seed": 20260621,
            "early_stopping": True,
            "early_stopping_patience": 8,
            "class_weight": "balanced",
        },
        "score_total": 0.44,
        "score_directional_precision": 0.36,
        "score_coverage": 0.31,
        "score_generalization": 0.10,
        "score_stability": 0.10,
        "score_cost_penalty": 0.01,
        "decision": "keep_candidate",
        "decision_reasons_json": [],
    }
    repeated_parent = {
        **base_parent,
        "candidate_id": "parent-1-repeat",
        "model_version": "neural_eod_mlp_evo1_01_seed",
        "hyperparameters_json": {
            **base_parent["hyperparameters_json"],
            "random_seed": 20260701,
        },
        "score_total": 0.43,
    }
    different_family = {
        **base_parent,
        "candidate_id": "parent-2",
        "model_version": "neural_eod_mlp_evo1_02",
        "hyperparameters_json": {
            **base_parent["hyperparameters_json"],
            "dropout_rate": 0.25,
        },
        "score_total": 0.42,
    }
    fake_client.leaderboard_rows = [base_parent, repeated_parent, different_family]
    monkeypatch.setattr(module, "_BQ_CLIENT", fake_client)

    candidates = module._generate_phase2_candidates(
        client=fake_client,
        evolution_run_id="run-phase2",
        dataset_snapshot="snapshot_2026",
        budget=module.EvolutionBudget(max_trials=4, random_seed=42),
        existing_hashes=set(),
        model_version_prefix="evo2_test",
        payload={
            "phase2": {
                "top_fraction": 1.0,
                "parent_limit": 3,
                "max_parents_per_family": 1,
                "include_seed_repeats": False,
            }
        },
    )

    parent_notes = [candidate.training_request["notes"] for candidate in candidates]

    assert len(candidates) == 4
    assert any("neural_eod_mlp_evo1_01" in notes for notes in parent_notes)
    assert any("neural_eod_mlp_evo1_02" in notes for notes in parent_notes)
    assert not any("neural_eod_mlp_evo1_01_seed" in notes for notes in parent_notes)


def test_orchestrator_phase2_falls_back_to_architecture_variants_when_grid_exhausted(
    monkeypatch,
):
    fake_client = _FakeClient()
    parent = {
        "candidate_id": "parent-1",
        "evolution_run_id": "run-phase1",
        "model_version": "neural_eod_mlp_evo1_01",
        "model_id": "neural_eod_mlp",
        "candidate_source": "deterministic",
        "architecture_json": {
            "type": "mlp",
            "hidden_units": [128, 64],
            "batch_norm": False,
        },
        "hyperparameters_json": {
            "dropout_rate": 0.15,
            "learning_rate": 0.001,
            "batch_size": 256,
            "epochs": 40,
            "random_seed": 20260621,
            "early_stopping": True,
            "early_stopping_patience": 8,
            "class_weight": "balanced",
        },
        "score_total": 0.44,
        "score_directional_precision": 0.36,
        "score_coverage": 0.31,
        "score_generalization": 0.10,
        "score_stability": 0.10,
        "score_cost_penalty": 0.01,
        "decision": "keep_candidate",
        "decision_reasons_json": [],
    }
    fake_client.leaderboard_rows = [parent]
    monkeypatch.setattr(module, "_BQ_CLIENT", fake_client)

    parent_candidate = module._phase2_parent_candidates(fake_client, limit=1)[0][0]
    exhausted_mutations = module.mutate_top_candidates(
        [parent_candidate],
        evolution_run_id="old-run",
        dataset_snapshot="snapshot_2026",
        budget=module.EvolutionBudget(max_trials=3, random_seed=42),
        existing_hashes=set(),
        model_version_prefix="old_mutation",
    )

    candidates = module._generate_phase2_candidates(
        client=fake_client,
        evolution_run_id="run-phase2",
        dataset_snapshot="snapshot_2026",
        budget=module.EvolutionBudget(max_trials=2, random_seed=42),
        existing_hashes={candidate.dedupe_hash for candidate in exhausted_mutations},
        model_version_prefix="evo2_test",
        payload={
            "phase2": {
                "top_fraction": 1.0,
                "parent_limit": 1,
                "max_parents_per_family": 1,
                "include_seed_repeats": False,
            }
        },
    )

    assert len(candidates) == 2
    assert {candidate.candidate_source for candidate in candidates} == {
        "architecture_variant"
    }
    assert all(
        candidate.model_version.startswith("evo2_test_arch_")
        for candidate in candidates
    )
    assert all(
        candidate.architecture["hidden_units"]
        != parent["architecture_json"]["hidden_units"]
        for candidate in candidates
    )
    assert not (
        {candidate.dedupe_hash for candidate in candidates}
        & {candidate.dedupe_hash for candidate in exhausted_mutations}
    )


def test_orchestrator_phase3_generates_new_family_candidates(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(module, "_BQ_CLIENT", fake_client)

    response, status = module.neural_evolution_orchestrator(
        _Request(
            {
                "dry_run": True,
                "strategy": "phase3_new_families",
                "budget": {"max_trials": 2, "random_seed": 42},
            }
        )
    )

    assert status == 200
    assert response["strategy"] == "phase3_new_families"
    assert response["candidate_count"] == 2
    assert response["candidate_sources"] == ["phase3_family"]
    assert set(response["architecture_types"]) <= {
        "residual_mlp",
        "wide_deep_mlp",
        "tabular_bottleneck_mlp",
    }
    assert all("phase3" in candidate for candidate in response["candidates"])
    assert all(
        detail["candidate_source"] == "phase3_family"
        for detail in response["candidate_details"]
    )

    candidates = module._generate_candidates_for_strategy(
        client=fake_client,
        strategy="phase3_new_families",
        evolution_run_id="run-phase3",
        dataset_snapshot="snapshot_2026",
        budget=module.EvolutionBudget(max_trials=2, random_seed=42),
        existing_hashes=set(),
        model_version_prefix="phase3_test",
        payload={},
    )

    assert {candidate.candidate_source for candidate in candidates} == {"phase3_family"}
    assert all(
        candidate.training_request["architecture_type"]
        == candidate.architecture["type"]
        for candidate in candidates
    )
    assert {candidate.model_id for candidate in candidates} <= {
        "neural_eod_residual_mlp",
        "neural_eod_wide_deep_mlp",
        "neural_eod_tabular_bottleneck_mlp",
    }


def test_orchestrator_dry_run_does_not_persist_or_call_training(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(module, "_BQ_CLIENT", fake_client)

    def fail_training(payload):  # pragma: no cover - should not be called
        raise AssertionError("training should not be called in dry_run")

    monkeypatch.setattr(module, "_invoke_training", fail_training)

    response, status = module.neural_evolution_orchestrator(
        _Request({"dry_run": True, "budget": {"max_trials": 1, "random_seed": 42}})
    )

    assert status == 200
    assert response["dry_run"] is True
    assert response["candidate_count"] == 1
    assert fake_client.loaded == []


def test_metrics_from_registry_accepts_json_string():
    metrics = {"test": {"coverage": 0.4}}

    assert (
        module._metrics_from_registry({"metrics_json": json.dumps(metrics)}) == metrics
    )


def test_orchestrator_persists_muen_economics_when_registry_metrics_include_folds(
    monkeypatch,
):
    fake_client = _FakeClient()
    monkeypatch.setattr(module, "_BQ_CLIENT", fake_client)

    def fake_invoke_training(payload):
        fake_client.registry_by_version[payload["model_version"]] = {
            "model_version": payload["model_version"],
            "metrics_json": {
                "train": {"accuracy": 0.50},
                "validation": {"accuracy": 0.46, "directional_precision": 0.42},
                "test": {
                    "accuracy": 0.44,
                    "coverage": 0.35,
                    "directional_precision": 0.43,
                },
                "muen_economics": {
                    "candidate_family_hash": "family-ready",
                    "seed_count": 3,
                    "fold_metrics": [
                        {
                            "fold_id": "fold_01",
                            "trades": 20,
                            "coverage": 0.4,
                            "expectancy_net": 0.03,
                            "median_net_return": 0.02,
                            "total_net_return": 0.6,
                            "profit_factor": 2.0,
                            "max_drawdown": 0.05,
                            "positive_trade_ratio": 0.7,
                            "delta_expectancy_vs_champion": 0.02,
                            "cost_multiplier": 1.0,
                        },
                        {
                            "fold_id": "fold_02",
                            "trades": 20,
                            "coverage": 0.4,
                            "expectancy_net": 0.031,
                            "median_net_return": 0.021,
                            "total_net_return": 0.62,
                            "profit_factor": 2.1,
                            "max_drawdown": 0.04,
                            "positive_trade_ratio": 0.75,
                            "delta_expectancy_vs_champion": 0.021,
                            "cost_multiplier": 1.5,
                        },
                    ],
                },
            },
        }
        return {"status": "ok", "model_version": payload["model_version"]}

    monkeypatch.setattr(module, "_invoke_training", fake_invoke_training)

    response, status = module.neural_evolution_orchestrator(
        _Request(
            {
                "evolution_run_id": "run-muen-ready",
                "model_version_prefix": "evo_muen_ready",
                "budget": {"max_trials": 1, "random_seed": 42},
            }
        )
    )

    loaded = dict(fake_client.loaded)

    assert status == 200
    assert response["fold_metric_count"] == 2
    assert response["family_evaluation_count"] == 1
    assert response["gate_decision_count"] == 1
    assert "ingestaokraken.cotacao_intraday.neural_fold_metrics" in loaded
    assert "ingestaokraken.cotacao_intraday.neural_family_evaluations" in loaded
    gate_rows = loaded["ingestaokraken.cotacao_intraday.neural_gate_decisions"]
    assert gate_rows[0]["decision_status"] == "rejected"
    assert "muen_economics_missing" not in gate_rows[0]["failed_criteria"]
