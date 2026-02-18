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
    result = dq_main.CheckResult(name="demo", component="table", status="FAIL", details={})
    assert result.severity == "CRITICAL"
    result_pass = dq_main.CheckResult(name="demo", component="table", status="PASS", details={})
    assert result_pass.severity == "INFO"
