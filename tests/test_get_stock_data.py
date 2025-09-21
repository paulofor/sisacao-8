import importlib
import os
import sys


def test_get_stock_data_success(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "google.cloud.bigquery",
        type("x", (), {"Client": lambda *a, **k: None}),
    )
    sys.path.insert(
        0,
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    )
    module = importlib.import_module("functions.get_stock_data.main")

    monkeypatch.setattr(
        module,
        "download_from_b3",
        lambda tickers: {"YDUQ3": ("2025-01-01", 10.0)},
    )
    monkeypatch.setattr(
        module,
        "load_tickers_from_file",
        lambda file_path=None: ["YDUQ3"],
    )
    monkeypatch.setattr(
        module,
        "append_dataframe_to_bigquery",
        lambda df: None,
    )
    response = module.get_stock_data(None)
    assert response == "Success"
