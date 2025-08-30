"""Simple price scraper for Google Finance.

This module provides utilities to fetch the latest price for a ticker
from Google Finance. The main function ``fetch_google_finance_price``
performs an HTTP request and parses the HTML, but a smaller
``extract_price_from_html`` helper is exposed for easier testing.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

import requests  # type: ignore[import-untyped]
from bs4 import BeautifulSoup  # type: ignore[import-untyped]

# Timeout in seconds for HTTP requests
TIMEOUT = 10

logger = logging.getLogger(__name__)


def _parse_number(value: str) -> float:
    """Convert a price string into a float.

    Parameters
    ----------
    value:
        Price string such as ``"R$ 10,50"``.

    Returns
    -------
    float
        Parsed numeric value.

    Raises
    ------
    ValueError
        If the value cannot be converted to ``float``.
    """

    cleaned = re.sub(r"[^0-9.,-]", "", value)
    if cleaned.count(",") == 1 and cleaned.count(".") == 0:
        cleaned = cleaned.replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")

    try:
        return float(cleaned)
    except ValueError as exc:
        raise ValueError(f"Could not parse price text: {value}") from exc


def extract_price_from_html(html: str) -> float:
    """Extract the price value from a Google Finance HTML page.

    The function searches for the div containing the price using the
    ``YMlKec`` and ``fxKbKc`` classes used by Google Finance. The returned
    price is a float in Brazilian Real.

    Parameters
    ----------
    html:
        Raw HTML string from the Google Finance page.

    Returns
    -------
    float
        Parsed price value.

    Raises
    ------
    ValueError
        If the price element is not found or cannot be parsed.
    """

    soup = BeautifulSoup(html, "html.parser")
    price_div = soup.select_one("div.YMlKec.fxKbKc")
    if price_div is None:
        raise ValueError("Could not find price element in HTML")

    price_text = price_div.get_text(strip=True)
    return _parse_number(price_text)


def fetch_google_finance_price(
    ticker: str,
    exchange: str = "BVMF",
    session: Optional[requests.Session] = None,
) -> float:
    """Fetch the latest price for ``ticker`` from Google Finance.

    Parameters
    ----------
    ticker:
        Stock ticker symbol, e.g. ``"YDUQ3"``.
    exchange:
        Exchange suffix used by Google Finance, default ``"BVMF"``.
    session:
        Optional ``requests.Session`` to reuse connections.

    Returns
    -------
    float
        Latest price for the ticker.
    """

    url = f"https://www.google.com/finance/quote/{ticker}:{exchange}"
    logger.warning("Fetching Google Finance URL %s for ticker %s", url, ticker)
    sess = session or requests
    headers = {"User-Agent": "Mozilla/5.0"}
    response = sess.get(url, headers=headers, timeout=TIMEOUT)
    logger.warning(
        "Received response with status %s for ticker %s",
        response.status_code,
        ticker,
    )
    response.raise_for_status()
    price = extract_price_from_html(response.text)
    logger.warning("Extracted price %.2f for ticker %s", price, ticker)
    return price
