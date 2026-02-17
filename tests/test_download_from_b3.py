import datetime
import importlib
import io
import sys
import zipfile
from pathlib import Path
from typing import List

import pytest
import requests  # type: ignore[import-untyped]

sys.path.append(str(Path(__file__).resolve().parents[1]))




def make_candle(module, ticker="YDUQ3", date="2025-01-01", price=12.34):
    timestamp = datetime.datetime.strptime(date, "%Y-%m-%d").replace(
        tzinfo=module.SAO_PAULO_TZ
    )
    return module.Candle(
        ticker=ticker,
        timestamp=timestamp,
        open=price,
        high=price,
        low=price,
        close=price,
        volume=1000.0,
        source=module.FONTE_FECHAMENTO,
        timeframe=module.Timeframe.DAILY,
        ingested_at=timestamp,
    )



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
    monkeypatch.setattr(main, "parse_b3_daily_zip", lambda *args, **kwargs: [make_candle(main)])

    result = download_from_b3(["YDUQ3"], date=datetime.date(2025, 1, 1))
    candle = result["YDUQ3"]
    assert candle.close == pytest.approx(12.34)
    assert candle.reference_date.isoformat() == "2025-01-01"


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
    assert result["YDUQ3"].close == pytest.approx(12.97)


def test_download_from_b3_records_diagnostics_on_error(monkeypatch):
    """Record proxy errors in diagnostics list."""

    monkeypatch.setattr("google.cloud.bigquery.Client", lambda: None)
    main = importlib.import_module("functions.get_stock_data.main")
    download_from_b3 = main.download_from_b3

    def mock_get(*args, **kwargs):  # noqa: ANN001, ANN002 - match requests.get
        raise requests.exceptions.ProxyError("proxy failed")

    monkeypatch.setattr(requests, "get", mock_get)

    diagnostics: List[str] = []
    result = download_from_b3(
        ["YDUQ3"],
        date=datetime.date(2025, 1, 1),
        diagnostics=diagnostics,
    )
    assert result["YDUQ3"].close == pytest.approx(12.97)
    assert any("proxy failed" in item for item in diagnostics)


def test_build_b3_daily_filenames_uses_ddmmaaaa(monkeypatch):
    """Ensure daily B3 filenames are generated in DDMMAAAA format."""

    monkeypatch.setattr("google.cloud.bigquery.Client", lambda: None)
    main = importlib.import_module("functions.get_stock_data.main")

    token, zip_name, txt_name = main._build_b3_daily_filenames(
        datetime.date(2026, 2, 9)
    )

    assert token == "09022026"
    assert zip_name == "COTAHIST_D09022026.ZIP"
    assert txt_name == "COTAHIST_D09022026.TXT"


def test_download_from_b3_requests_ddmmaaaa_filename(monkeypatch):
    """Ensure request URL contains daily DDMMAAAA filename."""

    monkeypatch.setattr("google.cloud.bigquery.Client", lambda: None)
    main = importlib.import_module("functions.get_stock_data.main")
    download_from_b3 = main.download_from_b3

    requested_urls = []

    class DummyResponse:
        content = b""

        def raise_for_status(self) -> None:
            """Pretend response is OK."""

    def mock_get(url, *args, **kwargs):  # noqa: ANN001, ANN002 - match requests.get
        requested_urls.append(url)
        return DummyResponse()

    monkeypatch.setattr(requests, "get", mock_get)

    download_from_b3(["YDUQ3"], date=datetime.date(2026, 2, 9))

    assert requested_urls
    assert requested_urls[0].endswith("/COTAHIST_D09022026.ZIP")


def test_download_from_b3_fallbacks_after_404(monkeypatch):
    """Fallback to previous day when latest file returns 404."""

    monkeypatch.setattr("google.cloud.bigquery.Client", lambda: None)
    main = importlib.import_module("functions.get_stock_data.main")
    download_from_b3 = main.download_from_b3

    requested_urls = []

    prefix = "01" + "20260211" + "  " + "YDUQ3      "
    line = prefix + " " * (108 - 24) + "0000000001500\n"

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("COTAHIST_D11022026.TXT", line)
    buffer.seek(0)

    class NotFoundResponse:
        status_code = 404
        content = b""

        def raise_for_status(self) -> None:
            response = requests.Response()
            response.status_code = 404
            raise requests.exceptions.HTTPError("404", response=response)

    class OkResponse:
        status_code = 200
        content = buffer.getvalue()

        def raise_for_status(self) -> None:
            return None

    def mock_get(url, *args, **kwargs):  # noqa: ANN001, ANN002 - match requests.get
        requested_urls.append(url)
        if url.endswith("/COTAHIST_D12022026.ZIP"):
            return NotFoundResponse()
        return OkResponse()

    monkeypatch.setattr(requests, "get", mock_get)

    monkeypatch.setattr(main, "parse_b3_daily_zip", lambda *args, **kwargs: [make_candle(main, date="2026-02-11", price=15.0)])
    result = download_from_b3(["YDUQ3"], date=datetime.date(2026, 2, 12))

    candle = result["YDUQ3"]
    assert candle.close == pytest.approx(15.0)
    assert requested_urls[0].endswith("/COTAHIST_D12022026.ZIP")
    assert requested_urls[1].endswith("/COTAHIST_D11022026.ZIP")
