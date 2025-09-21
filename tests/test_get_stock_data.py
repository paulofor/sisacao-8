import importlib
import os
import sys
import types


def import_get_stock_module(monkeypatch):
    fake_bigquery = types.ModuleType("bigquery")
    fake_bigquery.Client = lambda *a, **k: None
    fake_cloud = types.ModuleType("cloud")
    fake_cloud.bigquery = fake_bigquery
    fake_google = types.ModuleType("google")
    fake_google.cloud = fake_cloud
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.cloud", fake_cloud)
    monkeypatch.setitem(sys.modules, "google.cloud.bigquery", fake_bigquery)
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)
    module_name = "functions.get_stock_data.main"
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


def test_get_stock_data_success(monkeypatch):
    module = import_get_stock_module(monkeypatch)

    monkeypatch.setattr(
        module,
        "download_from_b3",
        lambda tickers: {"YDUQ3": ("2025-01-01", 10.0)},
    )
    monkeypatch.setattr(module, "load_tickers_from_file", lambda path=None: ["YDUQ3"])
    monkeypatch.setattr(
        module,
        "append_dataframe_to_bigquery",
        lambda df: None,
    )
    response = module.get_stock_data(None)
    assert response == "Success"


def test_load_tickers_from_file(monkeypatch, tmp_path):
    module = import_get_stock_module(monkeypatch)
    tickers_file = tmp_path / "tickers.txt"
    tickers_file.write_text("# teste\nYDUQ3\n petr4 \nYDUQ3\n", encoding="utf-8")
    tickers = module.load_tickers_from_file(tickers_file)
    assert tickers == ["YDUQ3", "PETR4"]
