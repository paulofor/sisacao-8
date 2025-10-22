import json
import sys

json.dump(
    [
        {
            "id": "test-1",
            "collector": "unit-test",
            "severity": "SUCCESS",
            "summary": "ok",
            "dataset": "test.dataset",
            "createdAt": "2024-01-01T00:00:00Z",
            "metadata": {"count": 1},
        }
    ],
    sys.stdout,
)
