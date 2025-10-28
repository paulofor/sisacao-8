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
    with pytest.raises(ModuleNotFoundError) as excinfo:
        gf_scraper.extract_price_from_html("<div></div>")
    assert "beautifulsoup4" in str(excinfo.value)


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
    assert (
        captured["url"]
        == "https://www.google.com/finance/quote/IBOV:INDEXBVMF"  # noqa: E501
    )
