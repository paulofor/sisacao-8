import json
from pathlib import Path

import pytest
import requests

from functions.google_finance_price import google_scraper as gf_scraper


def test_extract_price_from_html_success():
    html = '<div class="YMlKec fxKbKc">R$ 10,50</div>'
    assert gf_scraper.extract_price_from_html(html) == pytest.approx(10.50)


def test_extract_price_from_html_data_attribute():
    html = '<div data-last-price="123.45"></div>'
    assert gf_scraper.extract_price_from_html(html) == pytest.approx(123.45)


def test_extract_price_from_html_json_payload():
    html = '<script>"price": {"raw": 87.65, "fmt": "R$ 87,65"}</script>'
    assert gf_scraper.extract_price_from_html(html) == pytest.approx(87.65)


def test_extract_price_from_html_jsname_container():
    html = (
        '<div jsname="ip75Cb"><div class="YMlKec">R$ 21,30</div></div>'
    )
    assert gf_scraper.extract_price_from_html(html) == pytest.approx(21.30)


def test_extract_price_from_html_missing():
    with pytest.raises(ValueError):
        gf_scraper.extract_price_from_html("<div></div>")


def test_extract_price_from_html_wrong_class():
    html = '<div class="fxKbKc">R$ 10,50</div>'
    with pytest.raises(ValueError):
        gf_scraper.extract_price_from_html(html)


def test_extract_price_from_html_without_bs4(monkeypatch):
    monkeypatch.setattr(gf_scraper, "BeautifulSoup", None)
    price = gf_scraper.extract_price_from_html(
        '<div class="YMlKec fxKbKc">R$ 10,50</div>'
    )
    assert price == pytest.approx(10.50)


def test_extract_price_from_html_attribute_fallback():
    html = (
        '<div data-last-price="-"></div>'
        '<div class="YMlKec fxKbKc">R$ 10,50</div>'
    )
    assert gf_scraper.extract_price_from_html(html) == pytest.approx(10.50)


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

    test_results_path = (
        Path(__file__).resolve().parents[1]
        / "frontend"
        / "app"
        / "public"
        / "test-results"
        / "google-finance-parser.json"
    )

    fallback_results_path = (
        Path(__file__).resolve().parent / "fixtures" / "google-finance-parser.json"
    )

    for results_path in (test_results_path, fallback_results_path):
        if results_path.exists():
            test_results = json.loads(results_path.read_text(encoding="utf-8"))
            break
    else:
        pytest.skip("Nenhum fixture de resultado de parser encontrado")

    price = gf_scraper.extract_price_from_html(html_content)

    assert price == pytest.approx(test_results["details"]["parsedPrice"])
    assert test_results["status"].lower() == "passed"
    assert test_results["details"]["ticker"] == "PETR4"
    assert test_results["details"]["exchange"] == "BVMF"
    assert test_results["details"]["parsedPrice"] == pytest.approx(price)

    price_text = test_results["details"]["priceText"]
    assert price_text.startswith("R$")
    assert price_text[2:] == f"{price:.2f}"

    assert "updatedAt" in test_results
    # Ensure the timestamp follows the ISO-8601 format produced by datetime.isoformat.
    assert "T" in test_results["updatedAt"]


def test_fetch_google_finance_price_uses_batchexecute_fallback(monkeypatch):
    html_content = """
    <html lang="pt-BR">
        <head>
            <script>
                window.WIZ_global_data = {"cfb2h":"test_build","FdrFJe":"123456789"};
            </script>
        </head>
    </html>
    """

    quote_payload = [
        "/g/12fh0ph_n",
        ["TEST", "BVMF"],
        "Test Corp",
        0,
        "BRL",
        [42.42, 0, 0, 2, 2, 2],
        None,
        42.0,
        "#000000",
        "BR",
        None,
        [1770831703],
    ]
    raw_data = [[["/g/12fh0ph_n", None, None, quote_payload]]]
    frame = ["wrb.fr", "mKsvE", json.dumps(raw_data), None, None, None, "generic"]
    api_payload_lines = [
        ")]}'",
        "",
        str(len(frame[2])),
        json.dumps([frame]),
    ]
    api_payload = "\n".join(api_payload_lines)

    class DummyResponse:
        def __init__(self, text: str, status: int = 200):
            self.text = text
            self.status_code = status

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.HTTPError(f"status {self.status_code}")

    class DummySession:
        def get(self, *_args, **_kwargs):
            return DummyResponse(html_content)

        def post(self, *_args, **_kwargs):
            return DummyResponse(api_payload)

    def fake_extract(_html: str) -> float:  # noqa: D401, ANN001
        raise ValueError("missing price")

    monkeypatch.setattr(gf_scraper, "extract_price_from_html", fake_extract)

    price = gf_scraper.fetch_google_finance_price("test", session=DummySession())
    assert price == pytest.approx(42.42)


def test_has_unresolved_ticker_title():
    unresolved_html = "<html><head><title>BPAN4 - Google Finance</title></head></html>"
    resolved_html = (
        "<html><head><title>Banco Pan SA (BPAN4) Stock Price &amp; News - Google Finance"
        "</title></head></html>"
    )

    assert gf_scraper._has_unresolved_ticker_title(unresolved_html, "BPAN4")
    assert not gf_scraper._has_unresolved_ticker_title(resolved_html, "BPAN4")


def test_fetch_google_finance_price_prioritizes_unresolved_title_fallback(monkeypatch):
    html_content = "<html><head><title>BPAN4 - Google Finance</title></head></html>"

    class DummyResponse:
        status_code = 200
        text = html_content

        def raise_for_status(self):
            return None

    class DummySession:
        def get(self, *_args, **_kwargs):
            return DummyResponse()

    def fake_extract(_html: str) -> float:  # noqa: D401, ANN001
        raise AssertionError("extract_price_from_html should not run for unresolved pages")

    def fake_fallback(*_args, **_kwargs):  # noqa: D401, ANN001
        return 17.35

    monkeypatch.setattr(gf_scraper, "extract_price_from_html", fake_extract)
    monkeypatch.setattr(gf_scraper, "_fetch_price_from_batchexecute", fake_fallback)

    price = gf_scraper.fetch_google_finance_price("BPAN4", session=DummySession())
    assert price == pytest.approx(17.35)
