"""Cloud Run function to fetch Google Finance prices."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from .google_scraper import fetch_google_finance_price


def google_finance_price(request: Any) -> Tuple[Dict[str, float | str], int]:
    """HTTP Cloud Run entry point returning latest price for a ticker.

    Parameters
    ----------
    request:
        Object with an ``args`` attribute mimicking Flask's ``Request``.

    Returns
    -------
    tuple
        A pair ``(body, status_code)`` suitable for Cloud Run responses.
    """

    ticker = request.args.get("ticker", "YDUQ3")
    try:
        price = fetch_google_finance_price(ticker)
        return {"ticker": ticker, "price": price}, 200
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}, 500
