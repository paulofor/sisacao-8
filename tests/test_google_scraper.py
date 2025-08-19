import pytest

from scripts.google_scraper import extract_price_from_html


def test_extract_price_from_html_success():
    html = '<div class="YMlKec fxKbKc">R$ 10,50</div>'
    assert extract_price_from_html(html) == pytest.approx(10.50)


def test_extract_price_from_html_missing():
    with pytest.raises(ValueError):
        extract_price_from_html("<div></div>")
