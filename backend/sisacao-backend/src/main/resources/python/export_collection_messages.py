#!/usr/bin/env python3
"""Generate monitoring messages based on Python data collectors."""

from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _utc_now_iso() -> str:
    """Return current UTC time in ISO format with ``Z`` suffix."""

    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _ensure_fake_bigquery() -> None:
    """Provide a dummy BigQuery client to avoid credential requirements."""

    import types

    google_module = sys.modules.setdefault(
        "google",
        types.ModuleType("google"),
    )
    cloud_module = getattr(google_module, "cloud", None)
    if cloud_module is None:
        cloud_module = types.ModuleType("cloud")
        google_module.cloud = cloud_module
        sys.modules["google.cloud"] = cloud_module

    bigquery_module = types.ModuleType("bigquery")

    class _DummyClient:  # noqa: D401 - simple stub
        def __init__(self, *args: object, **kwargs: object) -> None:
            return None

    bigquery_module.Client = _DummyClient  # type: ignore[attr-defined]
    cloud_module.bigquery = bigquery_module
    sys.modules["google.cloud.bigquery"] = bigquery_module


def _error_message(
    collector: str,
    dataset: str,
    summary: str,
    error: BaseException,
) -> Dict[str, Any]:
    """Return an error message payload."""

    return {
        "id": f"{collector}-error-{int(time.time() * 1000)}",
        "collector": collector,
        "severity": "ERROR",
        "summary": summary,
        "dataset": dataset,
        "createdAt": _utc_now_iso(),
        "metadata": {"error": str(error)},
    }


def _load_tickers(get_stock_module: Any) -> List[str]:
    """Load configured tickers using the helper from ``get_stock_data``."""

    tickers_path = (
        Path(__file__).resolve().parents[1]
        / "get_stock_data"
        / "tickers.txt"
    )
    tickers = get_stock_module.load_tickers_from_file(tickers_path)
    return tickers or ["YDUQ3", "PETR4"]


def _collect_b3_message() -> Dict[str, Any]:
    """Collect closing prices using ``get_stock_data`` helpers."""

    _ensure_fake_bigquery()
    from functions.get_stock_data import (  # noqa: WPS433
        main as get_stock_module,
    )

    tickers = _load_tickers(get_stock_module)
    tickers = tickers[:10]
    today = dt.date.today()

    attempts: List[Tuple[str, str]] = []
    for offset in range(0, 5):
        target_date = today - dt.timedelta(days=offset)
        try:
            data = get_stock_module.download_from_b3(tickers, date=target_date)
        except Exception as exc:  # noqa: BLE001
            attempts.append((target_date.isoformat(), f"exception: {exc}"))
            continue

        if data:
            metadata = {
                "fonte": get_stock_module.FONTE_FECHAMENTO,
                "arquivoReferencia": target_date.isoformat(),
                "tickersSolicitados": tickers,
                "linhasProcessadas": len(data),
                "cotacoes": [
                    {
                        "ticker": ticker,
                        "dataPregao": date_str,
                        "precoFechamento": round(float(price), 2),
                    }
                    for ticker, (date_str, price) in data.items()
                ],
            }
            summary = (
                f"Cotações de fechamento obtidas para {len(data)} tickers "
                f"(arquivo {target_date.isoformat()})."
            )
            dataset = (
                f"{get_stock_module.DATASET_ID}."
                f"{get_stock_module.FECHAMENTO_TABLE_ID}"
            )
            return {
                "id": f"get-stock-data-{int(time.time() * 1000)}",
                "collector": "get_stock_data",
                "severity": "SUCCESS",
                "summary": summary,
                "dataset": dataset,
                "createdAt": _utc_now_iso(),
                "metadata": metadata,
            }
        attempts.append((target_date.isoformat(), "sem dados"))

    dataset = (
        f"{get_stock_module.DATASET_ID}."
        f"{get_stock_module.FECHAMENTO_TABLE_ID}"
    )
    error = RuntimeError(
        f"Nenhum dado retornado pelas últimas tentativas: {attempts}"
    )
    return _error_message(
        "get_stock_data",
        dataset,
        "Falha ao obter cotações de fechamento da B3.",
        error,
    )


def _collect_google_message() -> Dict[str, Any]:
    """Collect intraday prices using the Google Finance scraper."""

    _ensure_fake_bigquery()

    from functions.get_stock_data import (  # noqa: WPS433
        main as get_stock_module,
    )
    from functions.google_finance_price import (  # noqa: WPS433
        main as google_module,
    )
    from functions.google_finance_price.google_scraper import (  # noqa: WPS433
        fetch_google_finance_price,
    )

    tickers = _load_tickers(get_stock_module)
    tickers = tickers[:5]

    results: List[Dict[str, Any]] = []
    errors: Dict[str, str] = {}
    for ticker in tickers:
        try:
            price = fetch_google_finance_price(ticker)
        except Exception as exc:  # noqa: BLE001
            errors[ticker] = str(exc)
            continue
        results.append({"ticker": ticker, "valor": round(float(price), 2)})

    dataset = f"{google_module.DATASET_ID}.{google_module.TABELA_ID}"

    if results and not errors:
        severity = "SUCCESS"
        summary = f"Preços intraday capturados para {len(results)} tickers."
    elif results:
        severity = "WARNING"
        summary = (
            "Preços intraday parcialmente capturados "
            f"({len(results)} sucesso, {len(errors)} falhas)."
        )
    else:
        severity = "ERROR"
        summary = "Não foi possível capturar preços no Google Finance."

    metadata: Dict[str, Any] = {
        "fonte": "google_finance",
        "tickersSolicitados": tickers,
    }
    if results:
        metadata["cotacoes"] = results
    if errors:
        metadata["falhas"] = errors

    message = {
        "id": f"google-finance-{int(time.time() * 1000)}",
        "collector": "google_finance_price",
        "severity": severity,
        "summary": summary,
        "dataset": dataset,
        "createdAt": _utc_now_iso(),
        "metadata": metadata,
    }
    if severity == "ERROR":
        message["metadata"]["error"] = errors
    return message


def main() -> None:
    messages: List[Dict[str, Any]] = []

    try:
        messages.append(_collect_b3_message())
    except Exception as exc:  # noqa: BLE001
        dataset = "cotacao_intraday.cotacao_fechamento_diario"
        messages.append(
            _error_message(
                "get_stock_data",
                dataset,
                "Falha inesperada ao coletar cotações de fechamento da B3.",
                exc,
            )
        )

    try:
        messages.append(_collect_google_message())
    except Exception as exc:  # noqa: BLE001
        dataset = "cotacao_intraday.cotacao_bovespa"
        messages.append(
            _error_message(
                "google_finance_price",
                dataset,
                "Falha inesperada ao coletar preços no Google Finance.",
                exc,
            )
        )

    json.dump(messages, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
