#!/usr/bin/env python3
"""Helper CLI to trigger Sisacao-8 reprocess flows with authentication."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import List, Mapping

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account

DEFAULT_REASON = "manual_reprocess"
DEFAULT_TIMEOUT = 60
JOB_GROUPS: Mapping[str, List[str]] = {
    "DAILY": ["get_stock_data"],
    "EOD": ["get_stock_data", "intraday_candles", "eod_signals"],
    "BACKTEST": ["backtest_daily"],
    "ALL": [
        "get_stock_data",
        "intraday_candles",
        "eod_signals",
        "backtest_daily",
        "dq_checks",
    ],
}


@dataclass
class JobResult:
    name: str
    status_code: int
    payload: Mapping[str, object] | None
    error: str | None = None


def _build_url(project: str, region: str, function_name: str) -> str:
    return f"https://{region}-{project}.cloudfunctions.net/{function_name}"


def _fetch_token(key_path: str, audience: str) -> str:
    credentials = service_account.IDTokenCredentials.from_service_account_file(
        key_path,
        target_audience=audience,
    )
    credentials.refresh(Request())
    return credentials.token


def _request_json(response: requests.Response) -> Mapping[str, object] | None:
    try:
        return response.json()
    except ValueError:
        if response.text:
            return {"raw": response.text}
    return None


def _invoke_job(
    *,
    key_path: str,
    url: str,
    payload: Mapping[str, object],
    timeout: int,
) -> JobResult:
    token = _fetch_token(key_path, url)
    response = requests.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    )
    result_payload = _request_json(response)
    if response.ok:
        return JobResult(
            name=url.rsplit("/", maxsplit=1)[-1],
            status_code=response.status_code,
            payload=result_payload,
        )
    error = result_payload or {"error": response.text}
    return JobResult(
        name=url.rsplit("/", maxsplit=1)[-1],
        status_code=response.status_code,
        payload=result_payload,
        error=json.dumps(error, ensure_ascii=False),
    )


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("date_ref", help="Data de referência (YYYY-MM-DD)")
    parser.add_argument(
        "--mode",
        choices=JOB_GROUPS.keys(),
        default="ALL",
        help="Pipeline padrão a ser reprocessado (default: ALL)",
    )
    parser.add_argument(
        "--jobs",
        help="Lista personalizada de funções (sobrepõe --mode)",
    )
    parser.add_argument("--project", required=True, help="ID do projeto GCP")
    parser.add_argument(
        "--region", default="us-central1", help="Região das Cloud Functions"
    )
    parser.add_argument(
        "--service-account-key",
        required=True,
        help="Caminho para o JSON da service account autorizada a invocar os jobs",
    )
    parser.add_argument(
        "--reason",
        default=DEFAULT_REASON,
        help="Motivo registrado nos logs (default: manual_reprocess)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Força execução mesmo fora das janelas padrão",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Timeout HTTP por job em segundos (default: 60)",
    )
    return parser.parse_args()


def _resolve_jobs(args: argparse.Namespace) -> List[str]:
    if args.jobs:
        return [job.strip() for job in args.jobs.split(",") if job.strip()]
    return JOB_GROUPS.get(args.mode.upper(), JOB_GROUPS["ALL"])


def main() -> int:
    args = _parse_arguments()
    jobs = _resolve_jobs(args)
    if not jobs:
        print("Nenhum job definido para execução", file=sys.stderr)
        return 1

    payload = {
        "date_ref": args.date_ref,
        "mode": args.mode.upper(),
        "force": args.force,
        "reason": args.reason or DEFAULT_REASON,
    }

    results: List[JobResult] = []
    for job in jobs:
        url = _build_url(args.project, args.region, job)
        print(f"Invocando {job} ({url})...", flush=True)
        try:
            result = _invoke_job(
                key_path=args.service_account_key,
                url=url,
                payload=payload,
                timeout=args.timeout,
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                JobResult(
                    name=job,
                    status_code=0,
                    payload=None,
                    error=str(exc),
                )
            )
            continue
        results.append(result)
        status = "OK" if result.error is None else "ERROR"
        print(f"→ {job}: {status} (HTTP {result.status_code})")
        if result.payload:
            print(json.dumps(result.payload, ensure_ascii=False, indent=2))
        if result.error:
            print(result.error, file=sys.stderr)

    failed = [r for r in results if r.error]
    if failed:
        print(f"\n{len(failed)} job(s) retornaram erro", file=sys.stderr)
        return 2
    print("\nTodos os jobs finalizaram com sucesso.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
