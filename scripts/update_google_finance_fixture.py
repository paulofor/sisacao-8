"""Utility to refresh the real Google Finance HTML fixture used in tests.

The script downloads the latest HTML for a configured ticker/exchange pair,
updates the fixture stored under ``tests/fixtures`` and refreshes the public
JSON consumed by the frontend to display the parser health status.

It is designed to run locally or inside CI automations (e.g. a scheduled
GitHub Action). Any parsing failure will exit with a non-zero status so the
caller can detect regressions early.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

# Ensure the repository root is available on the module search path so that we
# can import the Google Finance parser implementation without relying on
# PYTHONPATH being configured by the caller.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from functions.google_finance_price import google_scraper  # noqa: E402


DEFAULT_URL_TEMPLATE = "https://www.google.com/finance/quote/{ticker}:{exchange}"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "google_finance_PETR4.html"
TEST_RESULT_PATH = (
    REPO_ROOT
    / "frontend"
    / "app"
    / "public"
    / "test-results"
    / "google-finance-parser.json"
)


def _format_price_text(price: float, currency_prefix: str) -> str:
    """Return a display-friendly price string matching the existing UI."""

    return f"{currency_prefix}{price:.2f}"


def _load_existing_test_result() -> Optional[dict]:
    if not TEST_RESULT_PATH.exists():
        return None
    try:
        return json.loads(TEST_RESULT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _build_headers() -> dict[str, str]:
    """Return HTTP headers emulating a regular browser request."""

    return {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
    }


def refresh_fixture(ticker: str, exchange: str, currency_prefix: str = "R$") -> None:
    url = DEFAULT_URL_TEMPLATE.format(ticker=ticker, exchange=exchange)

    response = requests.get(url, headers=_build_headers(), timeout=15)
    response.raise_for_status()

    html_content = response.text
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(html_content, encoding="utf-8")

    parsed_price = google_scraper.extract_price_from_html(html_content)
    price_text = _format_price_text(parsed_price, currency_prefix)

    timestamp = datetime.now(tz=timezone.utc).replace(
        microsecond=0
    ).isoformat()

    test_result_payload = {
        "testName": "google_finance_parser_real_html",
        "description": (
            "Valida o parser de preços do Google Finance contra um HTML real "
            "da PETR4 na B3."
        ),
        "status": "passed",
        "updatedAt": timestamp,
        "details": {
            "ticker": ticker,
            "exchange": exchange,
            "priceText": price_text,
            "parsedPrice": parsed_price,
            "htmlFixture": str(FIXTURE_PATH.relative_to(REPO_ROOT)),
        },
    }

    previous_payload = _load_existing_test_result()
    if previous_payload and previous_payload.get("status") == "failed":
        # Preserve the last failure reason so we have context in the frontend.
        failure_reason = previous_payload.get("details", {}).get("error")
        if failure_reason:
            test_result_payload["details"]["previousError"] = failure_reason

    TEST_RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    TEST_RESULT_PATH.write_text(
        json.dumps(test_result_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Atualiza o fixture real do Google Finance usado nos testes."
        )
    )
    parser.add_argument(
        "--ticker",
        default="PETR4",
        help="Ticker monitorado (default: PETR4)",
    )
    parser.add_argument(
        "--exchange",
        default="BVMF",
        help="Bolsa/mercado do ticker (default: BVMF)",
    )
    parser.add_argument(
        "--currency-prefix",
        default="R$",
        help="Prefixo monetário exibido junto ao preço (default: R$)",
    )

    args = parser.parse_args()

    try:
        refresh_fixture(args.ticker, args.exchange, args.currency_prefix)
    except Exception as exc:  # noqa: BLE001
        timestamp = datetime.now(tz=timezone.utc).replace(
            microsecond=0
        ).isoformat()

        error_payload = {
            "testName": "google_finance_parser_real_html",
            "description": (
                "Valida o parser de preços do Google Finance contra um HTML real "
                "da PETR4 na B3."
            ),
            "status": "failed",
            "updatedAt": timestamp,
            "details": {
                "ticker": args.ticker,
                "exchange": args.exchange,
                "error": str(exc),
                "htmlFixture": str(FIXTURE_PATH.relative_to(REPO_ROOT)),
            },
        }

        TEST_RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        TEST_RESULT_PATH.write_text(
            json.dumps(error_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        raise


if __name__ == "__main__":
    main()
