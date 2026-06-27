from __future__ import annotations

import functions.neural_champion_approval.main as function_module
from sisacao8.neural_champion_approval import (
    ChampionApprovalRequest,
    audit_approved_champions,
    champion_approval_plan,
)


class _FakeQueryJob:
    def __init__(self, rows):
        self._rows = rows

    def result(self):
        return list(self._rows)


class _FakeClient:
    def __init__(self):
        self.registry = {}
        self.gates = {}
        self.updates = []
        self.queries = []
        self.loaded = {}

    def query(self, query, job_config=None):
        self.queries.append((query, job_config))
        if query.strip().startswith("UPDATE"):
            self.updates.append((query, job_config))
            return _FakeQueryJob([])
        if "FROM `ingestaokraken.cotacao_intraday.neural_model_registry`" in query:
            if "WHERE status = @status" in query:
                return _FakeQueryJob(
                    [
                        row
                        for row in self.registry.values()
                        if row["status"] == "approved"
                    ]
                )
            return _FakeQueryJob(list(self.registry.values())[:1])
        if "FROM `ingestaokraken.cotacao_intraday.neural_gate_decisions`" in query:
            return _FakeQueryJob(list(self.gates.values())[:1])
        raise AssertionError(query)

    def load_table_from_json(self, rows, table_id, job_config=None):
        self.loaded.setdefault(table_id, []).extend(list(rows))
        return _FakeQueryJob([])


class _Request:
    def __init__(self, body):
        self._body = body

    def get_json(self, silent=True):
        return self._body


def _passed_gate():
    return {
        "decision_id": "gate_passed_1",
        "protocol_version": "neural_eod_protocol_v1",
        "dataset_snapshot": "snapshot_2026",
        "candidate_family_hash": "family_hash",
        "gate_name": "research_walk_forward",
        "decision_status": "passed",
        "passed": True,
        "failed_criteria": [],
        "decided_at": "2026-06-25T10:00:00+00:00",
    }


def _registry(status="candidate"):
    return {
        "model_id": "neural_eod_mlp",
        "model_version": "model_v1",
        "status": status,
        "feature_version": "feature_eod_tabular_v1",
        "label_version": "label_eod_barrier_v2",
        "training_dataset_snapshot": "snapshot_2026",
        "artifact_uri": "gs://bucket/model_v1/model.keras",
        "notes": "",
    }


def test_champion_approval_plan_allows_passed_gate_candidate():
    request = ChampionApprovalRequest(
        model_version="model_v1",
        decision_id="gate_passed_1",
        approved_by="operador",
        approval_ticket="TICKET-1",
        dry_run=True,
    )

    plan = champion_approval_plan(
        request,
        registry_row=_registry(),
        gate_decision_row=_passed_gate(),
    )

    assert plan.approved is True
    assert plan.update_allowed is True
    assert plan.failed_checks == ()
    assert "decision_id=gate_passed_1" in (plan.approval_note or "")


def test_champion_approval_plan_blocks_missing_economics_gate():
    gate = _passed_gate() | {
        "decision_status": "blocked",
        "passed": False,
        "failed_criteria": ["muen_economics_missing"],
    }
    request = ChampionApprovalRequest(
        model_version="model_v1",
        decision_id="gate_passed_1",
        approved_by="operador",
        approval_ticket="TICKET-1",
    )

    plan = champion_approval_plan(
        request,
        registry_row=_registry(),
        gate_decision_row=gate,
    )

    assert plan.approved is False
    assert "gate_status_nao_passou" in plan.failed_checks
    assert "muen_economics_missing" in plan.failed_checks
    assert plan.update_allowed is False


def test_champion_approval_plan_is_idempotent_for_already_approved_model():
    request = ChampionApprovalRequest(
        model_version="model_v1",
        decision_id="gate_passed_1",
        approved_by="operador",
        approval_ticket="TICKET-1",
    )

    plan = champion_approval_plan(
        request,
        registry_row=_registry(status="approved"),
        gate_decision_row=_passed_gate(),
    )

    assert plan.approved is True
    assert plan.already_approved is True
    assert plan.update_allowed is False
    assert plan.warnings == ("modelo_ja_aprovado",)


def test_audit_approved_champions_flags_duplicates():
    rows = [
        _registry(status="approved"),
        _registry(status="approved") | {"model_version": "model_v2"},
        _registry(status="candidate") | {"model_version": "model_v3"},
    ]

    audit = audit_approved_champions(rows)

    assert audit.approved_count == 2
    assert audit.model_versions == ("model_v1", "model_v2")
    assert audit.warnings
    assert audit.warnings[0].startswith("champions_duplicados:")


def test_function_approve_if_passed_dry_run_does_not_update(monkeypatch):
    fake_client = _FakeClient()
    fake_client.registry["model_v1"] = _registry()
    fake_client.gates["gate_passed_1"] = _passed_gate()
    monkeypatch.setattr(function_module, "_BQ_CLIENT", fake_client)

    response, status = function_module.neural_champion_approval(
        _Request(
            {
                "mode": "approve_if_passed",
                "model_version": "model_v1",
                "decision_id": "gate_passed_1",
                "approved_by": "operador",
                "approval_ticket": "TICKET-1",
                "dry_run": True,
            }
        )
    )

    assert status == 200
    assert response["plan"]["approved"] is True
    assert response["plan"]["update_allowed"] is True
    assert fake_client.updates == []


def test_function_approve_if_passed_updates_when_not_dry_run(monkeypatch):
    fake_client = _FakeClient()
    fake_client.registry["model_v1"] = _registry()
    fake_client.gates["gate_passed_1"] = _passed_gate()
    monkeypatch.setattr(function_module, "_BQ_CLIENT", fake_client)

    response, status = function_module.neural_champion_approval(
        _Request(
            {
                "mode": "approve_if_passed",
                "model_version": "model_v1",
                "decision_id": "gate_passed_1",
                "approved_by": "operador",
                "approval_ticket": "TICKET-1",
                "dry_run": False,
            }
        )
    )

    assert status == 200
    assert response["plan"]["approved"] is True
    assert len(fake_client.updates) == 1
    assert "SET status = @status" in fake_client.updates[0][0]


def test_function_evaluate_candidate_is_explicitly_blocked(monkeypatch):
    fake_client = _FakeClient()
    fake_client.registry["model_v1"] = _registry()
    monkeypatch.setattr(function_module, "_BQ_CLIENT", fake_client)

    response, status = function_module.neural_champion_approval(
        _Request({"mode": "evaluate_candidate", "model_version": "model_v1"})
    )

    assert status == 409
    assert response["status"] == "blocked"
    assert response["reason"] == "muen_economics_missing"


def test_function_evaluate_candidate_persists_muen_rows(monkeypatch):
    fake_client = _FakeClient()
    fake_client.registry["model_v1"] = _registry() | {
        "metrics_json": {
            "muen_economics": {
                "protocol_version": "neural_eod_protocol_v1",
                "candidate_family_hash": "family_hash",
                "seed_count": 2,
                "fold_metrics": [
                    {
                        "fold_id": "fold_01",
                        "seed": 20260621,
                        "trades": 20,
                        "coverage": 0.4,
                        "expectancy_net": 0.03,
                        "median_net_return": 0.02,
                        "total_net_return": 0.6,
                        "profit_factor": 2.0,
                        "max_drawdown": 0.04,
                        "positive_trade_ratio": 0.75,
                        "delta_expectancy_vs_champion": 0.02,
                        "cost_multiplier": 1.0,
                    },
                    {
                        "fold_id": "fold_02",
                        "seed": 20260622,
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
            }
        }
    }
    monkeypatch.setattr(function_module, "_BQ_CLIENT", fake_client)

    response, status = function_module.neural_champion_approval(
        _Request(
            {
                "mode": "evaluate_candidate",
                "model_version": "model_v1",
                "dry_run": False,
            }
        )
    )

    assert status == 200
    assert response["fold_metric_count"] == 2
    assert response["family_evaluation_count"] == 1
    assert response["gate_decision_count"] == 1
    assert "ingestaokraken.cotacao_intraday.neural_fold_metrics" in fake_client.loaded
    assert (
        "ingestaokraken.cotacao_intraday.neural_family_evaluations"
        in fake_client.loaded
    )
    assert "ingestaokraken.cotacao_intraday.neural_gate_decisions" in fake_client.loaded
    gate_rows = fake_client.loaded[
        "ingestaokraken.cotacao_intraday.neural_gate_decisions"
    ]
    assert gate_rows[0]["failed_criteria"] != ["muen_economics_missing"]
