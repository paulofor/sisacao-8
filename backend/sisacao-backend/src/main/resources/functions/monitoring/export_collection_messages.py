#!/usr/bin/env python3
"""Generate monitoring messages based on Python data collectors."""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Set

DEFAULT_INTRADAY_DATASET = "cotacao_intraday.cotacao_bovespa"
DEFAULT_INTRADAY_TICKERS = ["PETR4", "VALE3", "IBOV"]


def _resolve_project_root() -> Path:
    """Best effort attempt to locate the project root directory."""

    candidates = []

    env_root = (
        os.environ.get("SISACAO_APP_ROOT")
        or os.environ.get("SISACAO_PROJECT_ROOT")
    )
    if env_root:
        candidates.append(Path(env_root).expanduser())

    script_path = Path(__file__).resolve()
    candidates.extend([script_path.parent, *script_path.parents])
    candidates.append(Path.cwd())

    checked: Set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in checked:
            continue
        checked.add(resolved)
        if (resolved / "functions").is_dir():
            return resolved

    return script_path.parent


ROOT_DIR = _resolve_project_root()
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

    tickers_path = ROOT_DIR / "functions" / "get_stock_data" / "tickers.txt"
    tickers = get_stock_module.load_tickers_from_file(tickers_path)
    return tickers or ["YDUQ3", "PETR4"]


def _read_tickers_from_file(path: Path) -> List[str]:
    """Return tickers defined in ``path`` without importing helper modules."""

    tickers: List[str] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                normalized = raw.strip().upper()
                if not normalized or normalized.startswith("#"):
                    continue
                if normalized not in tickers:
                    tickers.append(normalized)
    except OSError:
        return []
    return tickers


def _normalize_tickers(values: Iterable[str]) -> List[str]:
    """Normalize ticker collection into a unique, ordered list."""

    tickers: List[str] = []
    for raw in values:
        normalized = str(raw).strip().upper()
        if not normalized:
            continue
        if normalized not in tickers:
            tickers.append(normalized)
    return tickers


def _fallback_intraday_tickers() -> List[str]:
    """Return a deterministic list of tickers for intraday failures."""

    tickers_path = ROOT_DIR / "functions" / "get_stock_data" / "tickers.txt"
    configured = _read_tickers_from_file(tickers_path)
    if configured:
        return _normalize_tickers(configured)[:5]
    return DEFAULT_INTRADAY_TICKERS[:5]


def _build_intraday_failure_message(
    *,
    dataset: str,
    tickers: Iterable[str],
    summary: str,
    error: BaseException,
) -> Dict[str, Any]:
    """Generate a failure payload for intraday collections."""

    normalized_tickers = _normalize_tickers(tickers)
    if not normalized_tickers:
        normalized_tickers = DEFAULT_INTRADAY_TICKERS[:5]
    reason = f"{summary}: {error}"
    failures = {ticker: str(error) for ticker in normalized_tickers}
    metadata: Dict[str, Any] = {
        "fonte": "google_finance",
        "tickersSolicitados": normalized_tickers,
        "falhas": failures,
        "error": str(error),
    }
    return {
        "id": f"google-finance-error-{int(time.time() * 1000)}",
        "collector": "google_finance_price",
        "severity": "ERROR",
        "summary": reason,
        "dataset": dataset or DEFAULT_INTRADAY_DATASET,
        "createdAt": _utc_now_iso(),
        "metadata": metadata,
    }


def _collect_b3_message() -> Dict[str, Any]:
    """Collect closing prices using ``get_stock_data`` helpers."""

    _ensure_fake_bigquery()
    from functions.get_stock_data import (  # noqa: WPS433
        main as get_stock_module,
    )

    tickers = _load_tickers(get_stock_module)
    tickers = tickers[:10]
    today = dt.date.today()

    attempts: List[Dict[str, str]] = []
    for offset in range(0, 5):
        target_date = today - dt.timedelta(days=offset)
        diagnostics: List[str] = []
        try:
            data = get_stock_module.download_from_b3(
                tickers,
                date=target_date,
                diagnostics=diagnostics,
            )
        except Exception as exc:  # noqa: BLE001
            attempts.append(
                {
                    "data": target_date.isoformat(),
                    "motivo": f"exception: {exc}",
                }
            )
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

        motivo = diagnostics[-1] if diagnostics else "sem dados"
        attempts.append(
            {
                "data": target_date.isoformat(),
                "motivo": motivo,
            }
        )

    dataset = (
        f"{get_stock_module.DATASET_ID}."
        f"{get_stock_module.FECHAMENTO_TABLE_ID}"
    )
    # Access internal helper for deterministic fallback data.
    fallback_loader: Callable[[List[str], dt.date], Dict[str, Any]] = getattr(
        get_stock_module,
        "_fallback_b3_prices",
    )
    fallback_data = fallback_loader(
        tickers,
        today,
    )
    if fallback_data:
        summary = (
            "Cotações de fechamento simuladas com fallback offline "
            f"para {len(fallback_data)} tickers."
        )
        metadata = {
            "fonte": "b3_fallback",
            "arquivoReferencia": today.isoformat(),
            "tickersSolicitados": tickers,
            "linhasProcessadas": len(fallback_data),
            "cotacoes": [
                {
                    "ticker": ticker,
                    "dataPregao": date_str,
                    "precoFechamento": price,
                }
                for ticker, (date_str, price) in fallback_data.items()
            ],
            "tentativas": attempts,
        }
        return {
            "id": f"get-stock-data-warning-{int(time.time() * 1000)}",
            "collector": "get_stock_data",
            "severity": "WARNING",
            "summary": summary,
            "dataset": dataset,
            "createdAt": _utc_now_iso(),
            "metadata": metadata,
        }

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

    dataset = DEFAULT_INTRADAY_DATASET

    try:
        from functions.get_stock_data import (  # noqa: WPS433
            main as get_stock_module,
        )
    except Exception as exc:  # noqa: BLE001
        tickers = _fallback_intraday_tickers()
        summary = "Falha ao carregar módulo get_stock_data"
        return _build_intraday_failure_message(
            dataset=dataset,
            tickers=tickers,
            summary=summary,
            error=exc,
        )

    tickers = _load_tickers(get_stock_module)
    tickers = tickers[:5]

    try:
        from functions.google_finance_price import (  # noqa: WPS433
            main as google_module,
        )
    except Exception as exc:  # noqa: BLE001
        summary = "Falha ao carregar módulo google_finance_price"
        return _build_intraday_failure_message(
            dataset=dataset,
            tickers=tickers,
            summary=summary,
            error=exc,
        )

    dataset = (
        f"{getattr(google_module, 'DATASET_ID', 'cotacao_intraday')}"
        f".{getattr(google_module, 'TABELA_ID', 'cotacao_bovespa')}"
    )

    try:
        from functions.google_finance_price.google_scraper import (  # noqa: WPS433
            fetch_google_finance_price,
        )
    except Exception as exc:  # noqa: BLE001
        summary = "Falha ao carregar scraper do Google Finance"
        return _build_intraday_failure_message(
            dataset=dataset,
            tickers=tickers,
            summary=summary,
            error=exc,
        )

    results: List[Dict[str, Any]] = []
    errors: Dict[str, str] = {}
    for ticker in tickers:
        try:
            price = fetch_google_finance_price(ticker)
        except Exception as exc:  # noqa: BLE001
            errors[ticker] = str(exc)
            continue
        results.append({"ticker": ticker, "valor": round(float(price), 2)})

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
        message["metadata"]["error"] = errors or summary
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
