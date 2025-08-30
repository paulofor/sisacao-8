import datetime
import io
import logging
import os
import zipfile
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
TABELA_ID = "cotacao_bovespa"

# Timeout em segundos para requisições HTTP
TIMEOUT = 120

client = bigquery.Client()


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
    """Append a DataFrame to BigQuery table."""
    try:
        logging.warning(
            "DataFrame recebido com %s linhas e colunas %s",
            len(df),
            list(df.columns),
        )
        if "data" in df.columns:
            df["data"] = pd.to_datetime(df["data"]).dt.date
        if "hora" in df.columns:
            df["hora"] = pd.to_datetime(df["hora"], format="%H:%M").dt.time
        if "hora_atual" in df.columns:
            hora_atual_col = pd.to_datetime(df["hora_atual"], format="%H:%M")
            df["hora_atual"] = hora_atual_col.dt.time
        if "data_hora_atual" in df.columns:
            df["data_hora_atual"] = pd.to_datetime(df["data_hora_atual"])

        tabela_id = f"{client.project}.{DATASET_ID}.{TABELA_ID}"
        logging.warning("Tabela de destino: %s", tabela_id)
        job_config = bigquery.LoadJobConfig(
            schema=[
                bigquery.SchemaField("ticker", "STRING"),
                bigquery.SchemaField("data", "DATE"),
                bigquery.SchemaField("hora", "TIME"),
                bigquery.SchemaField("valor", "FLOAT"),
                bigquery.SchemaField("hora_atual", "TIME"),
                bigquery.SchemaField("data_hora_atual", "DATETIME"),
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
    """Entry point for the Cloud Function."""
    tickers = ["YDUQ3"]
    logging.warning("Processando ticker fixo: %s", tickers[0])

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
        hora_atual = datetime.datetime.now(brasil_tz).strftime("%H:%M")
        data_atual = datetime.datetime.now(brasil_tz).strftime("%Y-%m-%d")
        data_hora_atual = datetime.datetime.now(brasil_tz)
        logging.warning(
            "Horário atual calculado: %s %s",
            data_atual,
            hora_atual,
        )

        rows = []

        for ticker in tickers:
            ticker_info = data_dict.get(ticker)
            if ticker_info is not None:
                date_str, price = ticker_info
                logging.warning("Cotação obtida para %s: %.2f", ticker, price)
                rows.append(
                    {
                        "ticker": ticker,
                        "data": date_str,
                        "hora": "18:00",
                        "valor": round(price, 2),
                        "hora_atual": hora_atual,
                        "data_hora_atual": data_hora_atual,
                    }
                )
            else:
                logging.warning("Dados não disponíveis para %s", ticker)
                rows.append(
                    {
                        "ticker": ticker,
                        "data": data_atual,
                        "hora": None,
                        "valor": -1,
                        "hora_atual": hora_atual,
                        "data_hora_atual": data_hora_atual,
                    }
                )

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
