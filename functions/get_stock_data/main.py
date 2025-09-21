import datetime
import io
import logging
import os
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd  # type: ignore[import-untyped]
import requests  # type: ignore[import-untyped]
from google.cloud import bigquery  # type: ignore[import-untyped]
from pytz import timezone  # type: ignore[import-untyped]

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
TICKERS_FILE = Path(_env_tickers_path) if _env_tickers_path else DEFAULT_TICKERS_FILE


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
        logging.warning("Tickers carregados de %s: %s", path, tickers)
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


def download_from_b3(
    tickers: List[str], date: Optional[datetime.date] = None
) -> Dict[str, Tuple[str, float]]:
    """Download closing prices from official B3 daily file.

    Returns a mapping of ticker to a tuple (date, close_price).
    """
    if date is None:
        date = datetime.date.today()
    date_str = date.strftime("%Y%m%d")
    nome_arquivo_zip = f"COTAHIST_D{date_str}.ZIP"
    base_url = "https://www.b3.com.br/pesquisapregao/"
    url = f"{base_url}download?filelist={nome_arquivo_zip}"
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
                return result
            nome_arquivo = arquivos_txt[0]
            logging.warning("Arquivo dentro do ZIP: %s", nome_arquivo)
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
                    except ValueError:
                        logging.warning(
                            "Valor inválido para %s: %s",
                            ticker,
                            preco_str,
                        )
    except Exception as exc:  # noqa: BLE001
        logging.warning("Erro ao baixar arquivo da B3: %s", exc, exc_info=True)
    return result


def append_dataframe_to_bigquery(df: pd.DataFrame) -> None:
    """Append daily closing prices to the dedicated BigQuery table."""
    try:
        logging.warning(
            "DataFrame recebido com %s linhas e colunas %s",
            len(df),
            list(df.columns),
        )
        if "data_pregao" in df.columns:
            df["data_pregao"] = pd.to_datetime(df["data_pregao"]).dt.date
        if "data_captura" in df.columns:
            df["data_captura"] = pd.to_datetime(df["data_captura"])

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

        job = client.load_table_from_dataframe(
            df,
            tabela_id,
            job_config=job_config,
        )
        job.result()
        logging.warning(
            "DataFrame com %s linhas inserido com sucesso no BigQuery.",
            len(df),
        )
    except Exception as exc:  # noqa: BLE001
        logging.warning(
            "Erro ao inserir dados no BigQuery: %s",
            exc,
            exc_info=True,
        )


def get_stock_data(request):
    """Entry point for the Cloud Function that stores daily closing prices."""
    tickers = load_tickers_from_file()
    if not tickers:
        logging.warning("Nenhum ticker configurado para processamento.")
        return "No tickers configured"

    logging.warning(
        "Iniciando processamento de %s tickers configurados no arquivo.", len(tickers)
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

        df = pd.DataFrame(rows)
        logging.warning(
            "DataFrame final com %s linhas será enviado ao BigQuery.",
            len(df),
        )
        logging.warning("Pré-visualização do DataFrame:\n%s", df.head())
        append_dataframe_to_bigquery(df)

        return "Success"

    except Exception as exc:  # noqa: BLE001
        logging.warning("Erro geral: %s", exc, exc_info=True)
        return f"Erro geral: {exc}"
