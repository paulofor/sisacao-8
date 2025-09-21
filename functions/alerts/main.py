"""HTTP Cloud Function that sends daily signal alerts."""

from __future__ import annotations

import datetime
import logging
import os
from typing import Any, Dict, Tuple

import requests  # type: ignore[import-untyped]
from google.cloud import bigquery  # type: ignore[import-untyped]

LOG_LEVEL = os.environ.get("LOG_LEVEL", "WARNING").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.WARNING))

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
BQ_SIGNALS_TABLE = os.environ.get(
    "BQ_SIGNALS_TABLE", "ingestaokraken.cotacao_intraday.signals_oscilacoes"
)

client = bigquery.Client()


def alerts(request: Any) -> Tuple[Dict[str, Any], int]:
    """Fetch today's signals and optionally send a Telegram alert."""

    today = datetime.date.today()
    query = f"""
        SELECT ticker, COUNT(*) AS qtd
        FROM `{BQ_SIGNALS_TABLE}`
        WHERE dt = @dt
        GROUP BY ticker
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("dt", "DATE", today)]
    )
    rows = list(client.query(query, job_config=job_config))

    if not rows:
        logging.warning("No signals for %s", today)
        return {"message": f"No signals for {today.isoformat()}"}, 200

    summary_lines = [f"{row['ticker']}: {row['qtd']}" for row in rows]
    message = f"Sinais {today.isoformat()}\n" + "\n".join(summary_lines)
    logging.warning("Resumo de sinais:\n%s", message)

    if BOT_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message}
        try:
            resp = requests.post(url, json=payload, timeout=15)
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            logging.warning("Falha ao enviar alerta: %s", exc, exc_info=True)
            return {"error": str(exc)}, 500

    return {"rows": len(rows)}, 200
