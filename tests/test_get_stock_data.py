import importlib
import os
import sys


def test_no_tickers(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "google.cloud.bigquery",
        type("x", (), {"Client": lambda *a, **k: None}),
    )
    monkeypatch.setitem(
        sys.modules,
        "google.cloud.storage",
        type("x", (), {"Client": lambda *a, **k: None}),
    )
    sys.path.insert(
        0,
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    )
    module = importlib.import_module("functions.get_stock_data.main")

    monkeypatch.setattr(module, "get_tickers_from_gcs", lambda: [])
    monkeypatch.setattr(
        module,
        "append_dataframe_to_bigquery",
        lambda df: None,
    )
    response = module.get_stock_data(None)
    assert response == "Nenhum ticker encontrado no GCS."
