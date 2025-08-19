import datetime
import importlib
import io
import sys
import zipfile
from pathlib import Path

import requests  # type: ignore[import-untyped]

sys.path.append(str(Path(__file__).resolve().parents[1]))


def test_download_from_b3_returns_yduq3(monkeypatch):
    """Ensure YDUQ3 price is parsed from a mocked B3 file."""

    monkeypatch.setattr("google.cloud.bigquery.Client", lambda: None)
    main = importlib.import_module("functions.get_stock_data.main")
    download_from_b3 = main.download_from_b3

    prefix = "01" + "20250101" + "  " + "YDUQ3      "
    line = prefix + " " * (108 - 24) + "0000000001234\n"

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("dummy.txt", line)
    buffer.seek(0)

    class DummyResponse:
        content = buffer.getvalue()

        def raise_for_status(self) -> None:  # noqa: D401 - trivial
            """Pretend response is OK."""

    def mock_get(*args, **kwargs):  # noqa: ANN001, ANN002 - match requests.get
        return DummyResponse()

    monkeypatch.setattr(requests, "get", mock_get)

    result = download_from_b3(["YDUQ3"], date=datetime.date(2025, 1, 1))
    assert result["YDUQ3"] == ("2025-01-01", 12.34)


def test_download_from_b3_empty_zip(monkeypatch):
    """Return empty dict when ZIP has no text files."""

    monkeypatch.setattr("google.cloud.bigquery.Client", lambda: None)
    main = importlib.import_module("functions.get_stock_data.main")
    download_from_b3 = main.download_from_b3

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w"):
        pass
    buffer.seek(0)

    class DummyResponse:
        content = buffer.getvalue()

        def raise_for_status(self) -> None:  # noqa: D401 - trivial
            """Pretend response is OK."""

    def mock_get(*args, **kwargs):  # noqa: ANN001, ANN002 - match requests.get
        return DummyResponse()

    monkeypatch.setattr(requests, "get", mock_get)

    result = download_from_b3(["YDUQ3"], date=datetime.date(2025, 1, 1))
    assert result == {}
