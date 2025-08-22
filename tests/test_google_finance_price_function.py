from __future__ import annotations

from types import SimpleNamespace

import pytest

from functions.google_finance_price.main import google_finance_price


class DummyRequest(SimpleNamespace):
    """Minimal request object with an ``args`` attribute."""


def test_google_finance_price_success(monkeypatch):
    def mock_fetch(ticker: str, exchange: str = "BVMF", session=None) -> float:
        assert ticker == "YDUQ3"
        return 11.11

    monkeypatch.setattr(
        "functions.google_finance_price.main.fetch_google_finance_price",
        mock_fetch,
    )

    request = DummyRequest(args={"ticker": "YDUQ3"})
    body, status = google_finance_price(request)
    assert status == 200
    assert body["ticker"] == "YDUQ3"
    assert body["price"] == pytest.approx(11.11)


def test_google_finance_price_failure(monkeypatch):
    def mock_fetch(ticker: str, exchange: str = "BVMF", session=None) -> float:
        raise ValueError("boom")

    monkeypatch.setattr(
        "functions.google_finance_price.main.fetch_google_finance_price",
        mock_fetch,
    )

    request = DummyRequest(args={"ticker": "XYZ"})
    body, status = google_finance_price(request)
    assert status == 500
    assert "error" in body
