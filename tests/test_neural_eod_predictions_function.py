import datetime as dt
import importlib
import os
import sys
import types

import pandas as pd


def import_predictions_module(monkeypatch):
    fake_bigquery = types.ModuleType("bigquery")
    fake_bigquery.Client = lambda *args, **kwargs: None

    fake_storage = types.ModuleType("storage")
    fake_storage.Client = lambda *args, **kwargs: None

    fake_cloud = types.ModuleType("cloud")
    fake_cloud.bigquery = fake_bigquery
    fake_cloud.storage = fake_storage
    fake_google = types.ModuleType("google")
    fake_google.cloud = fake_cloud

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.cloud", fake_cloud)
    monkeypatch.setitem(sys.modules, "google.cloud.bigquery", fake_bigquery)
    monkeypatch.setitem(sys.modules, "google.cloud.storage", fake_storage)

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)

    module_name = "functions.neural_eod_predictions.main"
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


def test_has_reference_candles_requires_target_date(monkeypatch):
    module = import_predictions_module(monkeypatch)
    candles = pd.DataFrame(
        [
            {"ticker": "PETR4", "data_pregao": dt.date(2026, 7, 13)},
            {"ticker": "VALE3", "data_pregao": "2026-07-14"},
        ]
    )

    assert module._has_reference_candles(candles, dt.date(2026, 7, 14)) is True
    assert module._has_reference_candles(candles, dt.date(2026, 7, 15)) is False
    assert module._has_reference_candles(pd.DataFrame(), dt.date(2026, 7, 14)) is False


def test_recover_daily_candles_posts_reference_date(monkeypatch):
    module = import_predictions_module(monkeypatch)
    captured = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b"Success"

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = request.data.decode("utf-8")
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(module, "DAILY_CANDLES_RECOVERY_URL", "https://daily.example")
    monkeypatch.setattr(module, "DAILY_CANDLES_RECOVERY_TIMEOUT_SECONDS", 55)

    module._recover_daily_candles(dt.date(2026, 7, 14), force=True)

    assert captured == {
        "url": "https://daily.example",
        "body": (
            '{"date_ref": "2026-07-14", "force": true, '
            '"reason": "auto-recover-before-neural-eod-predictions"}'
        ),
        "timeout": 55,
    }
