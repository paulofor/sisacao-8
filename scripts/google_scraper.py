"""Simple price scraper for Google Finance.

This module provides utilities to fetch the latest price for a ticker
from Google Finance. The main function ``fetch_google_finance_price``
performs an HTTP request and parses the HTML, but a smaller
``extract_price_from_html`` helper is exposed for easier testing.
"""

from __future__ import annotations

import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

# Timeout in seconds for HTTP requests
TIMEOUT = 10


def extract_price_from_html(html: str) -> float:
    """Extract the price value from a Google Finance HTML page.

    The function searches for the div containing the price using the
    ``YMlKec`` class used by Google Finance. The returned price is a float
    in Brazilian Real.

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
    price_div = soup.find("div", class_="YMlKec")
    if price_div is None:
        raise ValueError("Could not find price element in HTML")

    # Clean the price string: remove currency symbols and normalize decimal
    # separator from comma to dot.
    price_text = price_div.text.strip()
    price_text = re.sub(r"[^0-9,]", "", price_text)
    if not price_text:
        raise ValueError("Price text is empty")

    return float(price_text.replace(",", "."))


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
    sess = session or requests
    headers = {"User-Agent": "Mozilla/5.0"}
    response = sess.get(url, headers=headers, timeout=TIMEOUT)
    response.raise_for_status()
    return extract_price_from_html(response.text)
