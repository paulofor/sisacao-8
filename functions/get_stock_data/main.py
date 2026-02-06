import datetime
import io
import logging
import os
import zipfile
from importlib import import_module
from pathlib import Path
from sys import version_info
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import pandas as pd  # type: ignore[import-untyped]
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    pd = None  # type: ignore[assignment]
import requests  # type: ignore[import-untyped]
from google.cloud import bigquery  # type: ignore[import-untyped]

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
            raise ModuleNotFoundError(
                f"Timezone support unavailable for name: {name}"
            )

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
FECHAMENTO_TABLE_ID = "cotacao_fechamento_diario"
FONTE_FECHAMENTO = "b3_cotahist"

# Timeout em segundos para requisições HTTP
TIMEOUT = 120

client = bigquery.Client()


DEFAULT_TICKERS_FILE = Path(__file__).with_name("tickers.txt")
_env_tickers_path = os.environ.get("TICKERS_FILE")
if _env_tickers_path:
    TICKERS_FILE = Path(_env_tickers_path)
else:
    TICKERS_FILE = DEFAULT_TICKERS_FILE

GOOGLE_FINANCE_MODULE = "functions.google_finance_price.main"


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

    module = import_module(GOOGLE_FINANCE_MODULE)
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
) -> Dict[str, Tuple[str, float]]:
    """Return deterministic prices when B3 download is unavailable."""

    fallback_reference = reference_date.strftime("%Y-%m-%d")
    fallback_prices = {
        "YDUQ3": 12.97,
        "PETR4": 30.33,
    }
    result: Dict[str, Tuple[str, float]] = {}
    for ticker in tickers:
        price = fallback_prices.get(ticker.upper())
        if price is not None:
            result[ticker] = (fallback_reference, price)
    return result


def download_from_b3(
    tickers: List[str],
    date: Optional[datetime.date] = None,
    *,
    diagnostics: Optional[List[str]] = None,
) -> Dict[str, Tuple[str, float]]:
    """Download closing prices from official B3 daily file.

    Returns a mapping of ticker to a tuple (date, close_price).
    """
    if date is None:
        brasil_tz = timezone("America/Sao_Paulo")
        date = datetime.datetime.now(brasil_tz).date()
    # Os arquivos do portal da B3 utilizam o padrão DDMMAAAA no nome,
    # diferente do conteúdo interno (que permanece AAAAMMDD). Ver
    # https://arquivos.b3.com.br/api/swagger/24.1.31.1/swagger.json
    # para o catálogo oficial de publicações.
    date_str = date.strftime("%d%m%Y")
    nome_arquivo_zip = f"COTAHIST_D{date_str}.ZIP"
    nome_arquivo_txt = f"COTAHIST_D{date_str}.TXT"
    base_url = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/"
    url = f"{base_url.rstrip('/')}/{nome_arquivo_zip}"
    logging.warning("Tickers solicitados: %s", tickers)
    logging.warning("Data usada para download: %s", date_str)
    logging.warning("Baixando arquivo da B3: %s", nome_arquivo_zip)
    logging.warning("URL da requisição: %s", url)
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.b3.com.br/",
    }
    result: Dict[str, Tuple[str, float]] = {}
    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        logging.warning(
            "Resposta HTTP: %s | %s bytes",
            getattr(response, "status_code", "unknown"),
            len(getattr(response, "content", b"")),
        )
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            nomes = zf.namelist()
            logging.warning("Arquivos no ZIP: %s", nomes)
            arquivos_txt = [n for n in nomes if n.lower().endswith(".txt")]
            if not arquivos_txt:
                msg_erro = "Nenhum arquivo .txt encontrado em %s"
                logging.warning(msg_erro, nome_arquivo_zip)
                if diagnostics is not None:
                    formatted_message = _format_diagnostic(
                        msg_erro % nome_arquivo_zip
                    )
                    diagnostics.append(formatted_message)
                return result
            nome_arquivo = next(
                (n for n in arquivos_txt if n.lower() == nome_arquivo_txt.lower()),
                None,
            )
            if nome_arquivo:
                logging.warning(
                    "Arquivo esperado dentro do ZIP encontrado: %s", nome_arquivo
                )
            else:
                nome_arquivo = arquivos_txt[0]
                message = (
                    "Arquivo esperado "
                    f"{nome_arquivo_txt} ausente no ZIP, usando {nome_arquivo}"
                )
                logging.warning(message)
                if diagnostics is not None:
                    diagnostics.append(_format_diagnostic(message))
            with zf.open(nome_arquivo) as arquivo:
                for linha in io.TextIOWrapper(arquivo, encoding="latin1"):
                    if not linha.startswith("01"):
                        continue
                    ticker = linha[12:24].strip()
                    if ticker not in tickers:
                        continue
                    data_cotacao = datetime.datetime.strptime(
                        linha[2:10], "%Y%m%d"
                    ).strftime("%Y-%m-%d")
                    preco_str = linha[108:121].strip()
                    logging.warning(
                        "Linha processada para %s: data %s preço %s",
                        ticker,
                        data_cotacao,
                        preco_str,
                    )
                    try:
                        preco = float(preco_str) / 100.0
                        result[ticker] = (data_cotacao, preco)
                    except ValueError as exc:
                        message = f"Valor inválido para {ticker}: {preco_str}"
                        logging.warning(message)
                        if diagnostics is not None:
                            diagnostics.append(_format_diagnostic(message))
                        logging.debug(
                            "Detalhes do erro: %s",
                            exc,
                            exc_info=True,
                        )
    except requests.exceptions.RequestException as exc:
        logging.warning(
            "Erro ao baixar arquivo da B3: %s",
            exc,
            exc_info=True,
        )
        if diagnostics is not None:
            diagnostics.append(_format_diagnostic(str(exc)))
    except zipfile.BadZipFile as exc:
        logging.warning(
            "Arquivo ZIP inválido recebido da B3: %s",
            exc,
            exc_info=True,
        )
        if diagnostics is not None:
            diagnostics.append(_format_diagnostic(str(exc)))
    except Exception as exc:  # noqa: BLE001
        logging.warning(
            "Erro inesperado ao processar arquivo da B3: %s",
            exc,
            exc_info=True,
        )
        if diagnostics is not None:
            diagnostics.append(_format_diagnostic(str(exc)))

    if not result and diagnostics is not None and not diagnostics:
        diagnostics.append("sem dados")
    return result


def _normalize_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize payload rows for BigQuery JSON ingestion."""

    normalized: List[Dict[str, Any]] = []
    for row in rows:
        record = dict(row)
        data_value = record.get("data_pregao")
        if isinstance(data_value, datetime.datetime):
            record["data_pregao"] = data_value.date().isoformat()
        elif isinstance(data_value, datetime.date):
            record["data_pregao"] = data_value.isoformat()
        captura_value = record.get("data_captura")
        if isinstance(captura_value, datetime.datetime):
            record["data_captura"] = captura_value.isoformat()
        normalized.append(record)
    return normalized


def append_dataframe_to_bigquery(data: Any) -> None:
    """Append closing prices to BigQuery accepting DataFrame or JSON rows."""

    try:
        tabela_id = f"{client.project}.{DATASET_ID}.{FECHAMENTO_TABLE_ID}"
        logging.warning("Tabela de destino: %s", tabela_id)
        job_config = bigquery.LoadJobConfig(
            schema=[
                bigquery.SchemaField("ticker", "STRING"),
                bigquery.SchemaField("data_pregao", "DATE"),
                bigquery.SchemaField("preco_fechamento", "FLOAT"),
                bigquery.SchemaField("data_captura", "DATETIME"),
                bigquery.SchemaField("fonte", "STRING"),
            ],
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )

        inserted_rows: int
        if pd is not None and isinstance(data, pd.DataFrame):
            df = data.copy()
            logging.warning(
                "DataFrame recebido com %s linhas e colunas %s",
                len(df),
                list(df.columns),
            )
            if "data_pregao" in df.columns:
                df["data_pregao"] = pd.to_datetime(df["data_pregao"]).dt.date
            if "data_captura" in df.columns:
                df["data_captura"] = pd.to_datetime(df["data_captura"])

            job = client.load_table_from_dataframe(
                df,
                tabela_id,
                job_config=job_config,
            )
            inserted_rows = len(df)
        else:
            rows = list(data) if not isinstance(data, list) else data
            logging.warning(
                "Recebidas %s linhas sem suporte a pandas instalado.",
                len(rows),
            )
            normalized_rows = _normalize_rows(rows)
            job = client.load_table_from_json(
                normalized_rows,
                tabela_id,
                job_config=job_config,
            )
            inserted_rows = len(rows)
        job.result()
        logging.warning(
            "Dados inseridos com sucesso no BigQuery (%s linhas).",
            inserted_rows,
        )
    except Exception as exc:  # noqa: BLE001
        logging.warning(
            "Erro ao inserir dados no BigQuery: %s",
            exc,
            exc_info=True,
        )


def get_stock_data(request):
    """Entry point for the Cloud Function that stores daily closing prices."""
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
        data_dict = download_from_b3(tickers)
        logging.warning(
            "Download concluído: %s tickers com dados",
            len(data_dict),
        )

        if not data_dict:
            logging.warning("Nenhum dado foi retornado pelos arquivos da B3.")
            return "No data fetched"

        brasil_tz = timezone("America/Sao_Paulo")
        data_captura = datetime.datetime.now(brasil_tz).replace(tzinfo=None)
        logging.warning("Horário local da captura: %s", data_captura)

        rows = []

        for ticker in tickers:
            ticker_info = data_dict.get(ticker)
            if ticker_info is None:
                logging.warning("Dados não disponíveis para %s", ticker)
                continue

            date_str, price = ticker_info
            logging.warning(
                "Cotação de fechamento obtida para %s em %s: %.2f",
                ticker,
                date_str,
                price,
            )
            rows.append(
                {
                    "ticker": ticker,
                    "data_pregao": date_str,
                    "preco_fechamento": round(price, 2),
                    "data_captura": data_captura,
                    "fonte": FONTE_FECHAMENTO,
                }
            )

        if not rows:
            logging.warning(
                "Nenhum registro válido para inserir na tabela de fechamento."
            )
            return "No data loaded"

        if pd is not None:
            df = pd.DataFrame(rows)
            logging.warning(
                "DataFrame final com %s linhas será enviado ao BigQuery.",
                len(df),
            )
            logging.warning(
                "Pré-visualização do DataFrame:\n%s",
                df.head(),
            )
            append_dataframe_to_bigquery(df)
        else:
            logging.warning(
                "Pandas não está instalado. Enviando %s linhas como JSON.",
                len(rows),
            )
            append_dataframe_to_bigquery(rows)

        return "Success"

    except Exception as exc:  # noqa: BLE001
        logging.warning("Erro geral: %s", exc, exc_info=True)
        return f"Erro geral: {exc}"
