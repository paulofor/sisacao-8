import json
import logging
from datetime import date

from sisacao8.observability import StructuredLogger


def test_structured_logger_outputs_json(caplog):
    logger = StructuredLogger("unit-test", run_id="run-123")
    logger.update_context(extra="value")
    with caplog.at_level(logging.INFO):
        payload = logger.ok("All good", date_ref=date(2024, 8, 12))
    assert payload["job_name"] == "unit-test"
    record = caplog.records[0]
    data = json.loads(record.message)
    assert data["status"] == "OK"
    assert data["run_id"] == "run-123"
    assert data["extra"] == "value"
    assert data["date_ref"] == "2024-08-12"
