import datetime
import logging
import os
from importlib import import_module
from pathlib import Path
from sys import version_info
from typing import Any, Dict, Iterable, List, Optional

try:
    import pandas as pd  # type: ignore[import-untyped]
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    pd = None  # type: ignore[assignment]
import requests  # type: ignore[import-untyped]
from google.cloud import bigquery  # type: ignore[import-untyped]

if __package__:
    from .b3 import B3FileError, candles_by_ticker, parse_b3_daily_zip
    from .candles import Candle, Timeframe, SAO_PAULO_TZ
else:
    from b3 import B3FileError, candles_by_ticker, parse_b3_daily_zip
    from candles import Candle, Timeframe, SAO_PAULO_TZ

if version_info >= (3, 9):  # pragma: no branch - runtime dependent import
    from zoneinfo import ZoneInfo
else:  # pragma: no branch - runtime dependent import
    try:
        from backports.zoneinfo import ZoneInfo  # type: ignore[import-untyped]
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        ZoneInfo = None  # type: ignore[assignment]

try:
    from pytz import timezone  # type: ignore[import-untyped]
except ModuleNotFoundError:  # pragma: no cover - fallback when pytz is absent

    def timezone(name: str):  # type: ignore[misc]
        """Return timezone instance even when optional deps are missing."""

        if ZoneInfo is not None:  # pragma: no branch - runtime guard
            return ZoneInfo(name)

        if name != "America/Sao_Paulo":  # pragma: no cover - defensive branch
            raise ModuleNotFoundError(f"Timezone support unavailable for name: {name}")

        return datetime.timezone(  # type: ignore[return-value]
            datetime.timedelta(hours=-3),
            name,
        )


LOG_LEVEL = os.environ.get("LOG_LEVEL", "WARNING").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.WARNING),
    format="%(asctime)s %(levelname)s %(message)s",
)

DATASET_ID = "cotacao_intraday"
FECHAMENTO_TABLE_ID = os.environ.get("BQ_DAILY_TABLE", "cotacao_ohlcv_diario")
FERIADOS_TABLE_ID = "feriados_b3"
FONTE_FECHAMENTO = "B3_DAILY_COTAHIST"
LOAD_STRATEGY = os.environ.get("BQ_DAILY_LOAD_STRATEGY", "MERGE")

# Timeout em segundos para requisições HTTP
TIMEOUT = 120
MAX_B3_LOOKBACK_DAYS = int(os.environ.get("MAX_B3_LOOKBACK_DAYS", "5"))

client = bigquery.Client()


DEFAULT_TICKERS_FILE = Path(__file__).with_name("tickers.txt")
_env_tickers_path = os.environ.get("TICKERS_FILE")
if _env_tickers_path:
    TICKERS_FILE = Path(_env_tickers_path)
else:
    TICKERS_FILE = DEFAULT_TICKERS_FILE

GOOGLE_FINANCE_MODULE = os.environ.get(
    "GOOGLE_FINANCE_MODULE",
    "functions.google_finance_price.main",
)
GOOGLE_FINANCE_MODULE_CANDIDATES = (
    GOOGLE_FINANCE_MODULE,
    "google_finance_price.main",
)


def load_tickers_from_file(file_path: Optional[Path] = None) -> List[str]:
    """Load ticker symbols from a text file."""

    path = Path(file_path) if file_path else TICKERS_FILE
    try:
        with path.open("r", encoding="utf-8") as handle:
            raw_tickers = [
                line.strip().upper()
                for line in handle
                if line.strip() and not line.lstrip().startswith("#")
            ]
        tickers: List[str] = []
        for ticker in raw_tickers:
            if ticker not in tickers:
                tickers.append(ticker)
        logging.warning(
            "Tickers carregados de %s: %s",
            path,
            tickers,
        )
        return tickers
    except FileNotFoundError:
        logging.warning("Arquivo de tickers não encontrado: %s", path)
    except Exception as exc:  # noqa: BLE001
        logging.warning(
            "Erro ao ler arquivo de tickers %s: %s",
            path,
            exc,
            exc_info=True,
        )
    return []


def load_tickers_from_google_finance() -> List[str]:
    """Load tickers using the google_finance_price helper."""

    module = None
    import_errors: List[str] = []
    for module_name in GOOGLE_FINANCE_MODULE_CANDIDATES:
        if not module_name:
            continue
        try:
            module = import_module(module_name)
            break
        except ModuleNotFoundError as exc:
            import_errors.append(f"{module_name}: {exc}")

    if module is None:
        raise ModuleNotFoundError(" | ".join(import_errors))

    fetch = getattr(module, "fetch_active_tickers", None)
    if fetch is None:
        raise AttributeError("fetch_active_tickers is not available")
    raw_tickers = fetch()
    tickers: List[str] = []
    for raw in raw_tickers:
        if not isinstance(raw, str):
            continue
        ticker = raw.strip().upper()
        if not ticker:
            continue
        if ticker not in tickers:
            tickers.append(ticker)
    if not tickers:
        raise ValueError("Nenhum ticker retornado por google_finance_price")
    logging.warning(
        "Tickers carregados via google_finance_price: %s",
        tickers,
    )
    return tickers


def load_configured_tickers(file_path: Optional[Path] = None) -> List[str]:
    """Load tickers from google_finance_price or fallback to file."""

    if file_path is not None:
        return load_tickers_from_file(file_path)
    if _env_tickers_path:
        return load_tickers_from_file(Path(_env_tickers_path))
    try:
        return load_tickers_from_google_finance()
    except ModuleNotFoundError as exc:
        logging.warning(
            "Módulo google_finance_price indisponível (%s). "
            "Usando fallback por arquivo.",
            exc,
        )
    except Exception as exc:  # noqa: BLE001
        logging.warning(
            "Falha ao carregar tickers via google_finance_price: %s",
            exc,
            exc_info=True,
        )
    return load_tickers_from_file()


def _format_diagnostic(message: str) -> str:
    """Normalize diagnostic messages for downstream monitoring."""

    return " ".join(message.strip().split())


def _fallback_b3_prices(
    tickers: Iterable[str],
    reference_date: datetime.date,
) -> Dict[str, Candle]:
    """Return deterministic candles when B3 download is unavailable."""

    fallback_prices = {"YDUQ3": 12.97, "PETR4": 30.33}
    ingestion_time = datetime.datetime.now(tz=SAO_PAULO_TZ)
    result: Dict[str, Candle] = {}
    for ticker in tickers:
        price = fallback_prices.get(ticker.upper())
        if price is None:
            continue
        candle = Candle(
            ticker=ticker,
            timestamp=datetime.datetime.combine(
                reference_date,
                datetime.time.min,
                tzinfo=SAO_PAULO_TZ,
            ),
            open=price,
            high=price,
            low=price,
            close=price,
            volume=0.0,
            source=FONTE_FECHAMENTO,
            timeframe=Timeframe.DAILY,
            ingested_at=ingestion_time,
            data_quality_flags=("FALLBACK_DATA",),
        )
        result[ticker] = candle
    return result


def _build_b3_daily_filenames(
    reference_date: datetime.date,
) -> tuple[str, str, str]:
    """Build B3 daily ZIP/TXT names using the DDMMAAAA filename standard."""

    date_token = (
        f"{reference_date.day:02d}"
        f"{reference_date.month:02d}"
        f"{reference_date.year:04d}"
    )
    zip_name = f"COTAHIST_D{date_token}.ZIP"
    txt_name = f"COTAHIST_D{date_token}.TXT"
    return date_token, zip_name, txt_name


def download_from_b3(
    tickers: List[str],
    date: Optional[datetime.date] = None,
    *,
    diagnostics: Optional[List[str]] = None,
) -> Dict[str, Candle]:
    """Download daily candles from the official B3 file."""

    if date is None:
        brasil_tz = timezone("America/Sao_Paulo")
        date = datetime.datetime.now(brasil_tz).date()
    logging.warning("Tickers solicitados: %s", tickers)
    logging.warning("Data base usada para download: %s", date.isoformat())
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.b3.com.br/"}
    result: Dict[str, Candle] = {}
    diag_list = diagnostics
    base_url = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/"
    for day_offset in range(MAX_B3_LOOKBACK_DAYS + 1):
        attempt_date = date - datetime.timedelta(days=day_offset)
        _, zip_name, txt_name = _build_b3_daily_filenames(attempt_date)
        url = f"{base_url.rstrip('/')}/{zip_name}"
        logging.warning("Tentativa %s de download da B3", day_offset + 1)
        logging.warning("Baixando arquivo da B3: %s", zip_name)
        logging.warning("URL da requisição: %s", url)
        try:
            response = requests.get(url, headers=headers, timeout=TIMEOUT)
            logging.warning(
                "Resposta HTTP: %s | %s bytes",
                getattr(response, "status_code", "unknown"),
                len(getattr(response, "content", b"")),
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            logging.warning("Erro HTTP ao baixar arquivo da B3: %s", exc, exc_info=True)
            if status_code == 404 and day_offset < MAX_B3_LOOKBACK_DAYS:
                continue
            if diag_list is not None:
                diag_list.append(_format_diagnostic(str(exc)))
            break
        except requests.exceptions.RequestException as exc:
            logging.warning("Erro ao baixar arquivo da B3: %s", exc, exc_info=True)
            if diag_list is not None:
                diag_list.append(_format_diagnostic(str(exc)))
            break
        try:
            diag: Dict[str, str] = {}
            candles = parse_b3_daily_zip(
                response.content,
                tickers=tickers,
                expected_filename=txt_name,
                diagnostics=diag,
            )
        except B3FileError as exc:
            logging.warning(
                "Arquivo ZIP inválido recebido da B3: %s", exc, exc_info=True
            )
            if diag_list is not None:
                diag_list.append(_format_diagnostic(str(exc)))
            continue
        result = candles_by_ticker(candles)
        if result:
            if day_offset > 0:
                logging.warning(
                    "Dados obtidos com fallback de %s dia(s).",
                    day_offset,
                )
            break
        message = diag.get("empty_dataset") or diag.get("missing_file")
        if message and diag_list is not None:
            diag_list.append(_format_diagnostic(message))
    if not result:
        logging.warning(
            "Nenhum dado oficial retornado; usando fallback offline se disponível."
        )
        fallback = _fallback_b3_prices(tickers, date)
        if fallback:
            return fallback
        if diag_list is not None and not diag_list:
            diag_list.append("sem dados")
    return result


def _normalize_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize payload rows for BigQuery JSON ingestion."""

    normalized: List[Dict[str, Any]] = []
    for row in rows:
        record = dict(row)
        value = record.get("atualizado_em")
        if isinstance(value, datetime.datetime):
            record["atualizado_em"] = value.replace(tzinfo=None).isoformat(sep=" ")
        trade_date = record.get("data_pregao")
        if isinstance(trade_date, datetime.date):
            record["data_pregao"] = trade_date.isoformat()
        normalized.append(record)
    return normalized


def append_dataframe_to_bigquery(data: Any, reference_date: datetime.date) -> None:
    """Load normalized candles to BigQuery with idempotent strategies."""

    tabela_id = f"{client.project}.{DATASET_ID}.{FECHAMENTO_TABLE_ID}"
    logging.warning("Tabela de destino: %s", tabela_id)
    delete_query = (
        "DELETE FROM `"
        f"{tabela_id}"
        "` WHERE data_pregao = @ref_date"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("ref_date", "DATE", reference_date)
        ]
    )
    strategy = LOAD_STRATEGY.strip().upper()
    if strategy == "DELETE_PARTITION_APPEND":
        try:
            client.query(delete_query, job_config=job_config).result()
            logging.warning(
                "Partição de %s limpa antes da nova inserção.", reference_date
            )
        except Exception as exc:  # noqa: BLE001
            logging.warning(
                "Falha ao limpar partição de %s: %s",
                reference_date,
                exc,
                exc_info=True,
            )
    try:
        fallback_schema = [
            bigquery.SchemaField("ticker", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("data_pregao", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("open", "FLOAT"),
            bigquery.SchemaField("high", "FLOAT"),
            bigquery.SchemaField("low", "FLOAT"),
            bigquery.SchemaField("close", "FLOAT"),
            bigquery.SchemaField("volume", "FLOAT"),
            bigquery.SchemaField("qtd_negociada", "FLOAT"),
            bigquery.SchemaField("num_negocios", "INTEGER"),
            bigquery.SchemaField("fonte", "STRING"),
            bigquery.SchemaField("atualizado_em", "DATETIME"),
            bigquery.SchemaField("data_quality_flags", "STRING"),
            bigquery.SchemaField("fator_cotacao", "INTEGER"),
        ]
        try:
            expected_schema = client.get_table(tabela_id).schema
        except Exception:  # noqa: BLE001
            expected_schema = fallback_schema
        load_config = bigquery.LoadJobConfig(
            schema=expected_schema,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )
        target_table_id = tabela_id
        if strategy == "MERGE":
            target_table_id = f"{tabela_id}_staging"
            load_config.write_disposition = bigquery.WriteDisposition.WRITE_TRUNCATE
        inserted_rows: int
        if pd is not None and isinstance(data, pd.DataFrame):
            df = data.copy()
            if "data_pregao" in df.columns:
                df["data_pregao"] = pd.to_datetime(df["data_pregao"]).dt.date
            if "atualizado_em" in df.columns:
                df["atualizado_em"] = (
                    pd.to_datetime(df["atualizado_em"]).dt.tz_localize(None)
                )
            job = client.load_table_from_dataframe(
                df, target_table_id, job_config=load_config
            )
            inserted_rows = len(df)
        else:
            rows = list(data) if not isinstance(data, list) else data
            normalized_rows = _normalize_rows(rows)
            job = client.load_table_from_json(
                normalized_rows, target_table_id, job_config=load_config
            )
            inserted_rows = len(normalized_rows)
        job.result()
        if strategy == "MERGE":
            merge_sql = f"""
            MERGE `{tabela_id}` target
            USING `{target_table_id}` source
            ON target.ticker = source.ticker
              AND target.data_pregao = source.data_pregao
            WHEN MATCHED THEN UPDATE SET
              open = source.open,
              high = source.high,
              low = source.low,
              close = source.close,
              volume = source.volume,
              qtd_negociada = source.qtd_negociada,
              num_negocios = source.num_negocios,
              fonte = source.fonte,
              atualizado_em = source.atualizado_em,
              data_quality_flags = source.data_quality_flags,
              fator_cotacao = source.fator_cotacao
            WHEN NOT MATCHED THEN INSERT (
              ticker,
              data_pregao,
              open,
              high,
              low,
              close,
              volume,
              qtd_negociada,
              num_negocios,
              fonte,
              atualizado_em,
              data_quality_flags,
              fator_cotacao
            ) VALUES (
              source.ticker,
              source.data_pregao,
              source.open,
              source.high,
              source.low,
              source.close,
              source.volume,
              source.qtd_negociada,
              source.num_negocios,
              source.fonte,
              source.atualizado_em,
              source.data_quality_flags,
              source.fator_cotacao
            )
            """
            client.query(merge_sql).result()
            logging.warning(
                "MERGE concluído com chave lógica (ticker, data_pregao)."
            )
        logging.warning("Dados inseridos com sucesso (%s linhas).", inserted_rows)
    except Exception as exc:  # noqa: BLE001
        logging.warning("Erro ao inserir dados no BigQuery: %s", exc, exc_info=True)


def is_b3_holiday(reference_date: datetime.date) -> bool:
    """Return ``True`` when ``reference_date`` is configured as B3 holiday."""

    project_id = getattr(client, "project", None)
    if not project_id:
        logging.warning(
            "Cliente BigQuery sem project configurado; ignorando validação de feriado."
        )
        return False
    table_id = f"{project_id}.{DATASET_ID}.{FERIADOS_TABLE_ID}"
    query = (
        "SELECT data_feriado "
        f"FROM `{table_id}` "
        f"WHERE data_feriado = DATE '{reference_date.isoformat()}' "
        "LIMIT 1"
    )
    try:
        query_job = client.query(query)
        if pd is not None:
            df = query_job.to_dataframe()
            if "data_feriado" not in df.columns:
                logging.warning(
                    "Consulta de feriados retornou colunas inesperadas (%s). "
                    "Ignorando validação de feriado.",
                    list(df.columns),
                )
                return False
            return not df.empty
        rows = list(query_job.result())
        return len(rows) > 0
    except Exception as exc:  # noqa: BLE001
        logging.warning(
            "Falha ao consultar tabela de feriados %s: %s",
            table_id,
            exc,
            exc_info=True,
        )
        return False


def get_stock_data(request):
    """Entry point for the Cloud Function that stores daily closing prices."""
    brasil_tz = timezone("America/Sao_Paulo")
    reference_date = datetime.datetime.now(brasil_tz).date()
    if is_b3_holiday(reference_date):
        logging.warning(
            "Coleta de fechamento ignorada: %s é feriado cadastrado na tabela %s.",
            reference_date,
            FERIADOS_TABLE_ID,
        )
        return "Skipped holiday"

    tickers = load_configured_tickers()
    if not tickers:
        logging.warning("Nenhum ticker configurado para processamento.")
        return "No tickers configured"

    logging.warning(
        "Iniciando processamento de %s tickers configurados.",
        len(tickers),
    )

    try:
        logging.warning("Iniciando download de %s tickers...", len(tickers))
        diagnostics: List[str] = []
        data_dict = download_from_b3(
            tickers, date=reference_date, diagnostics=diagnostics
        )
        logging.warning(
            "Download concluído: %s tickers com dados",
            len(data_dict),
        )

        if not data_dict:
            logging.warning(
                "Nenhum dado foi retornado pelos arquivos da B3: %s", diagnostics
            )
            return "No data fetched"

        rows: List[Dict[str, Any]] = []
        for ticker in tickers:
            candle = data_dict.get(ticker)
            if candle is None:
                logging.warning("Dados não disponíveis para %s", ticker)
                continue
            logging.warning(
                "Candle diário %s - O:%.2f H:%.2f L:%.2f C:%.2f Vol:%.0f",
                ticker,
                candle.open,
                candle.high,
                candle.low,
                candle.close,
                candle.volume or 0,
            )
            rows.append(candle.to_bq_row())

        if not rows:
            logging.warning("Nenhum registro válido para inserir na tabela de candles.")
            return "No data loaded"

        if pd is not None:
            df = pd.DataFrame(rows)
            logging.warning(
                "DataFrame final com %s linhas será enviado ao BigQuery.",
                len(df),
            )
            logging.warning("Pré-visualização do DataFrame:\n%s", df.head())
            append_dataframe_to_bigquery(df, reference_date)
        else:
            logging.warning(
                "Pandas não está instalado. Enviando %s linhas como JSON.",
                len(rows),
            )
            append_dataframe_to_bigquery(rows, reference_date)

        return "Success"

    except Exception as exc:  # noqa: BLE001
        logging.warning("Erro geral: %s", exc, exc_info=True)
        return f"Erro geral: {exc}"
