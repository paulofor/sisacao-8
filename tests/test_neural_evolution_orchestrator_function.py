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
            return _FakeQueryJob([{"value": "label_eod_barrier_v1"}])
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
    evaluation_rows = fake_client.loaded[-1][1]
    assert evaluation_rows[0]["decision"] in {"keep_candidate", "shadow_candidate"}
    assert evaluation_rows[0]["score_total"] > 0


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
