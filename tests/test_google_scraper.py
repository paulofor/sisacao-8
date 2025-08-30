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
