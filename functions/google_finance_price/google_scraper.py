"""Simple price scraper for Google Finance.

This module provides utilities to fetch the latest price for a ticker
from Google Finance. The main function ``fetch_google_finance_price``
performs an HTTP request and parses the HTML, but a smaller
``extract_price_from_html`` helper is exposed for easier testing.
"""

from __future__ import annotations

import logging
import re
from html import unescape
from typing import Optional

import requests  # type: ignore[import-untyped]

try:
    from bs4 import BeautifulSoup  # type: ignore[import-untyped]
    from bs4 import FeatureNotFound  # type: ignore[import-untyped]
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    BeautifulSoup = None  # type: ignore[assignment]
    FeatureNotFound = None  # type: ignore[assignment]

# Timeout in seconds for HTTP requests
TIMEOUT = 10

logger = logging.getLogger(__name__)


def _extract_price_with_regex(html: str) -> float:
    """Extract price using a lightweight regex-based fallback."""

    pattern = re.compile(
        r"<div[^>]*class=(['\"])(?P<classes>[^'\"]*?)\1[^>]*>(?P<content>.*?)</div>",
        re.DOTALL,
    )
    for match in pattern.finditer(html):
        classes = set(match.group("classes").split())
        if {"YMlKec", "fxKbKc"}.issubset(classes):
            raw_content = re.sub(r"<[^>]+>", "", match.group("content"))
            price_text = unescape(raw_content).strip()
            if price_text:
                return _parse_number(price_text)
    raise ValueError("Could not find price element in HTML")


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

    if BeautifulSoup is not None:
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception as exc:  # pragma: no cover - defensive guard
            if FeatureNotFound is not None and isinstance(exc, FeatureNotFound):
                raise ModuleNotFoundError(
                    "BeautifulSoup requires an HTML parser. "
                    "Install the 'lxml' package with 'pip install lxml'."
                ) from exc
            logger.warning("BeautifulSoup failed to parse HTML", exc_info=True)
        else:
            price_div = soup.select_one("div.YMlKec.fxKbKc")
            if price_div is not None:
                price_text = price_div.get_text(strip=True)
                if price_text:
                    return _parse_number(price_text)
            logger.warning(
                "BeautifulSoup could not find price element; falling back to regex",
            )

    return _extract_price_with_regex(html)


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
    if ticker.upper() == "IBOV":
        url = "https://www.google.com/finance/quote/IBOV:INDEXBVMF"
    else:
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
