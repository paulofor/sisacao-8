from functions.dq_checks import main as dq_main


def test_coverage_status_pass():
    status, coverage = dq_main._coverage_status(available=9, expected=10, threshold=0.8)
    assert status == "PASS"
    assert round(coverage, 2) == 0.9


def test_coverage_status_warn_when_no_expected():
    status, coverage = dq_main._coverage_status(available=0, expected=0, threshold=0.9)
    assert status == "WARN"
    assert coverage == 0.0


def test_coverage_status_fail_when_below_threshold():
    status, coverage = dq_main._coverage_status(available=4, expected=10, threshold=0.8)
    assert status == "FAIL"
    assert round(coverage, 2) == 0.4


def test_check_result_severity_mapping():
    result = dq_main.CheckResult(
        name="demo",
        component="table",
        status="FAIL",
        details={},
    )
    assert result.severity == "CRITICAL"
    result_pass = dq_main.CheckResult(
        name="demo",
        component="table",
        status="PASS",
        details={},
    )
    assert result_pass.severity == "INFO"


def test_persist_results_serializes_check_date(monkeypatch):
    captured = {}

    class FakeJob:
        def result(self):
            return None

    class FakeClient:
        def load_table_from_json(self, rows, table_id, job_config):
            captured["rows"] = rows
            captured["table_id"] = table_id
            return FakeJob()

    monkeypatch.setattr(dq_main, "_get_client", lambda: FakeClient())
    monkeypatch.setattr(dq_main, "_table_ref", lambda table: f"project.dataset.{table}")

    dq_main._persist_results(
        dq_main.dt.date(2026, 6, 16),
        type("Logger", (), {"run_id": "run-1"})(),
        [
            dq_main.CheckResult(
                name="demo",
                component="component",
                status="PASS",
                details={
                    "reference_date": dq_main.dt.date(2026, 6, 16),
                    "deadline": dq_main.dt.time(22, 0),
                },
            )
        ],
        "test-config",
    )

    assert captured["rows"][0]["check_date"] == "2026-06-16"
    assert captured["rows"][0]["created_at"]
    assert '"reference_date": "2026-06-16"' in captured["rows"][0]["details"]
    assert '"deadline": "22:00:00"' in captured["rows"][0]["details"]


def test_persist_incidents_serializes_check_date(monkeypatch):
    captured = {}

    class FakeJob:
        def result(self):
            return None

    class FakeClient:
        def load_table_from_json(self, rows, table_id, job_config):
            captured["rows"] = rows
            captured["table_id"] = table_id
            return FakeJob()

    monkeypatch.setattr(dq_main, "_get_client", lambda: FakeClient())
    monkeypatch.setattr(dq_main, "_table_ref", lambda table: f"project.dataset.{table}")

    dq_main._persist_incidents(
        dq_main.dt.date(2026, 6, 16),
        type("Logger", (), {"run_id": "run-1"})(),
        [
            dq_main.CheckResult(
                name="demo",
                component="component",
                status="FAIL",
                details={},
            )
        ],
        "test-config",
    )

    assert captured["rows"][0]["check_date"] == "2026-06-16"
    assert captured["rows"][0]["created_at"]
