import json
from pathlib import Path

import pytest

from functions.google_finance_price import google_scraper as gf_scraper


def test_extract_price_from_html_success():
    html = '<div class="YMlKec fxKbKc">R$ 10,50</div>'
    assert gf_scraper.extract_price_from_html(html) == pytest.approx(10.50)


def test_extract_price_from_html_missing():
    with pytest.raises(ValueError):
        gf_scraper.extract_price_from_html("<div></div>")


def test_extract_price_from_html_wrong_class():
    html = '<div class="YMlKec">R$ 10,50</div>'
    with pytest.raises(ValueError):
        gf_scraper.extract_price_from_html(html)


def test_extract_price_from_html_without_bs4(monkeypatch):
    monkeypatch.setattr(gf_scraper, "BeautifulSoup", None)
    price = gf_scraper.extract_price_from_html(
        '<div class="YMlKec fxKbKc">R$ 10,50</div>'
    )
    assert price == pytest.approx(10.50)


def test_extract_price_from_html_missing_parser(monkeypatch):
    if gf_scraper.FeatureNotFound is None:
        pytest.skip("BeautifulSoup is not installed")

    class DummySoup:
        def __call__(self, *_args, **_kwargs):  # noqa: D401, ANN001
            raise gf_scraper.FeatureNotFound("lxml")

    monkeypatch.setattr(gf_scraper, "BeautifulSoup", DummySoup())

    with pytest.raises(ModuleNotFoundError) as excinfo:
        gf_scraper.extract_price_from_html("<div></div>")

    message = str(excinfo.value)
    assert "pip install lxml" in message


def test_fetch_google_finance_price_ibov(monkeypatch):
    captured = {}

    def fake_get(url, headers, timeout):  # noqa: D401, ANN001
        captured["url"] = url

        class DummyResponse:
            status_code = 200
            text = '<div class="YMlKec fxKbKc">R$ 10,50</div>'

            def raise_for_status(self):
                return None

        return DummyResponse()

    monkeypatch.setattr(gf_scraper.requests, "get", fake_get)
    price = gf_scraper.fetch_google_finance_price("IBOV")
    assert price == pytest.approx(10.50)
    expected_url = "https://www.google.com/finance/quote/IBOV:INDEXBVMF"
    assert captured["url"] == expected_url


def test_extract_price_from_real_google_finance_html():
    fixtures_dir = Path(__file__).resolve().parent / "fixtures"
    html_path = fixtures_dir / "google_finance_PETR4.html"
    html_content = html_path.read_text(encoding="utf-8")

    price = gf_scraper.extract_price_from_html(html_content)

    assert price == pytest.approx(29.75)

    test_results_path = (
        Path(__file__).resolve().parents[1]
        / "frontend"
        / "app"
        / "public"
        / "test-results"
        / "google-finance-parser.json"
    )
    test_results = json.loads(test_results_path.read_text(encoding="utf-8"))

    assert test_results["status"].lower() == "passed"
    assert test_results["details"]["ticker"] == "PETR4"
    assert test_results["details"]["exchange"] == "BVMF"
    assert test_results["details"]["priceText"] == "R$29.75"
    assert test_results["details"]["parsedPrice"] == pytest.approx(price)
