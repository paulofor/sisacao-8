"""Simple price scraper for Google Finance.

This module provides utilities to fetch the latest price for a ticker
from Google Finance. The main function ``fetch_google_finance_price``
performs an HTTP request and parses the HTML, but a smaller
``extract_price_from_html`` helper is exposed for easier testing.
"""

from __future__ import annotations

import json
import logging
import re
from html import unescape
from typing import Any, Dict, Optional

import requests  # type: ignore[import-untyped]

try:
    from bs4 import BeautifulSoup  # type: ignore[import-untyped]
    from bs4 import FeatureNotFound  # type: ignore[import-untyped]
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    BeautifulSoup = None  # type: ignore[assignment]
    FeatureNotFound = None  # type: ignore[assignment]

# Timeout in seconds for HTTP requests
TIMEOUT = 10

DATA_LAST_PRICE_RE = re.compile(
    r"data-last-price=(['\"])(?P<price>[^'\"]+)\1",
    re.IGNORECASE,
)

JSON_PRICE_RE = re.compile(
    r"\"price\"\s*:\s*\{\s*\"raw\"\s*:\s*(?P<price>-?[0-9.,]+)",
)

JSNAME_PRICE_RE = re.compile(
    (
        r"jsname=(['\"])ip75Cb\1[^>]*>"
        r"(?P<content>.*?)</div>"
    ),
    re.DOTALL,
)

HTML_LANG_RE = re.compile(
    r"<html[^>]*\blang=['""](?P<lang>[A-Za-z-]+)['""][^>]*>",
    re.IGNORECASE,
)

TITLE_RE = re.compile(r"<title>(?P<title>.*?)</title>", re.IGNORECASE | re.DOTALL)

logger = logging.getLogger(__name__)

WIZ_GLOBAL_DATA_RE = re.compile(
    r"window\.WIZ_global_data\s*=\s*(\{.*?\});",
    re.DOTALL,
)

DEFAULT_BUILD_LABEL = "boq_finance-ui_20260210.01_p0"
DEFAULT_LANG = "en"


class GoogleFinancePriceError(RuntimeError):
    """Custom exception that stores diagnostic details about failures."""

    def __init__(
        self,
        ticker: str,
        message: str,
        *,
        url: Optional[str] = None,
        status: Optional[int] = None,
        cause: Optional[BaseException] = None,
        response_excerpt: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.ticker = ticker
        self.url = url
        self.status = status
        self.cause = cause
        self.response_excerpt = response_excerpt
        base_details: Dict[str, Any] = {
            "ticker": ticker,
            "message": message,
            "type": self.__class__.__name__,
        }
        if url:
            base_details["url"] = url
        if status is not None:
            base_details["status"] = status
        if cause:
            base_details["cause"] = f"{cause.__class__.__name__}: {cause}"
        if response_excerpt:
            base_details["responseExcerpt"] = response_excerpt
        self._details = base_details

    def details(self) -> Dict[str, Any]:
        """Return a serialisable dictionary with diagnostic details."""

        # Return a shallow copy to keep the original dictionary immutable.
        details = dict(self._details)
        details.setdefault("message", str(self))
        return details


def _extract_price_with_regex(html: str) -> float:
    """Extract price using a lightweight regex-based fallback."""

    pattern = re.compile(
        (
            r"<div[^>]*class=(['\"])"
            r"(?P<classes>[^'\"]*?)\1[^>]*>"
            r"(?P<content>.*?)</div>"
        ),
        re.DOTALL,
    )
    for match in pattern.finditer(html):
        classes = set(match.group("classes").split())
        if "YMlKec" in classes:
            raw_content = re.sub(r"<[^>]+>", "", match.group("content"))
            price_text = unescape(raw_content).strip()
            if price_text:
                return _parse_number(price_text)
    raise ValueError("Could not find price element in HTML")


def _extract_price_from_data_attribute(html: str) -> float:
    """Extract price from ``data-last-price`` attribute when present."""

    match = DATA_LAST_PRICE_RE.search(html)
    if not match:
        raise ValueError("Could not find data-last-price attribute in HTML")

    price_text = match.group("price").strip()
    if not price_text or price_text in {"-", "—"}:
        raise ValueError("Invalid price attribute value")

    return _parse_number(price_text)


def _extract_price_from_json_payload(html: str) -> float:
    """Extract price from the embedded JSON payload in the HTML."""

    match = JSON_PRICE_RE.search(html)
    if not match:
        raise ValueError("Could not find price JSON payload in HTML")

    price_text = match.group("price").strip()
    return _parse_number(price_text)


def _extract_price_from_jsname_container(html: str) -> float:
    """Extract price from the ``jsname=ip75Cb`` container when present."""

    for match in JSNAME_PRICE_RE.finditer(html):
        content = match.group("content")
        price_match = re.search(
            r"class=(['\"])(?P<classes>[^'\"]*?\bYMlKec\b[^'\"]*)\1[^>]*>"
            r"(?P<price>[^<]+)",
            content,
            re.DOTALL,
        )
        if not price_match:
            continue
        price_text = unescape(price_match.group("price")).strip()
        if price_text:
            return _parse_number(price_text)
    raise ValueError("Could not find price in jsname container")


def _parse_number(value: str) -> float:
    """Convert a price string into a float.

    Parameters
    ----------
    value:
        Price string such as ``"R$ 10,50"``.

    Returns
    -------
    float
        Parsed numeric value.

    Raises
    ------
    ValueError
        If the value cannot be converted to ``float``.
    """

    cleaned = re.sub(r"[^0-9.,-]", "", value)
    if cleaned.count(",") == 1 and cleaned.count(".") == 0:
        cleaned = cleaned.replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")

    try:
        return float(cleaned)
    except ValueError as exc:
        raise ValueError(f"Could not parse price text: {value}") from exc


def extract_price_from_html(html: str) -> float:
    """Extract the price value from a Google Finance HTML page.

    The function searches for the div containing the price using the
    ``YMlKec`` and ``fxKbKc`` classes used by Google Finance. The returned
    price is a float in Brazilian Real.

    Parameters
    ----------
    html:
        Raw HTML string from the Google Finance page.

    Returns
    -------
    float
        Parsed price value.

    Raises
    ------
    ValueError
        If the price element is not found or cannot be parsed.
    """

    for extractor in (
        _extract_price_from_data_attribute,
        _extract_price_from_json_payload,
        _extract_price_from_jsname_container,
    ):
        try:
            return extractor(html)
        except ValueError:
            continue

    if BeautifulSoup is not None:
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception as exc:  # pragma: no cover - defensive guard
            if FeatureNotFound is not None and isinstance(
                exc, FeatureNotFound
            ):
                raise ModuleNotFoundError(
                    "BeautifulSoup requires an HTML parser. "
                    "Install the 'lxml' package with 'pip install lxml'."
                ) from exc
            logger.warning("BeautifulSoup failed to parse HTML", exc_info=True)
        else:
            selectors = [
                "div[jsname='ip75Cb'] div.YMlKec",
                "div.YMlKec.fxKbKc",
                "div.YMlKec",
            ]
            for selector in selectors:
                price_div = soup.select_one(selector)
                if price_div is None:
                    continue
                price_text = price_div.get_text(strip=True)
                if price_text:
                    return _parse_number(price_text)
            logger.warning(
                "BeautifulSoup could not find price element; falling back "
                "to regex",
            )

    return _extract_price_with_regex(html)


def _normalize_excerpt(value: str, limit: int = 280) -> str:
    """Return a compact excerpt limited by ``limit`` characters.

    The helper collapses whitespace and truncates the string when necessary.
    """

    # Collapse whitespace to keep the excerpt concise.
    cleaned = re.sub(r"\s+", " ", value).strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 3]}..."


def _extract_global_data(html: str) -> Dict[str, Any]:
    """Return the parsed ``window.WIZ_global_data`` dictionary if present."""

    match = WIZ_GLOBAL_DATA_RE.search(html)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        logger.warning(
            "Falha ao interpretar window.WIZ_global_data; ignorando fallback via API."
        )
        return {}


def _detect_page_language(html: str) -> str:
    """Infer the language declared in the ``<html>`` tag."""

    match = HTML_LANG_RE.search(html)
    if match:
        lang = match.group("lang").strip()
        if lang:
            return lang.split('-')[0]
    return DEFAULT_LANG


def _extract_wrapped_rpc_payload(payload: str, rpc_id: str) -> Optional[str]:
    """Return the JSON blob stored inside the batchexecute wrapper."""

    for line in payload.splitlines():
        line = line.strip()
        if not line or not line.startswith('[["wrb.fr"'):
            continue
        try:
            frame = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not frame or not isinstance(frame, list):
            continue
        current = frame[0]
        if not isinstance(current, list) or len(current) < 3:
            continue
        if current[1] == rpc_id:
            blob = current[2]
            if isinstance(blob, str) and blob:
                return blob
    return None


def _has_unresolved_ticker_title(html: str, ticker: str) -> bool:
    """Return ``True`` when Google Finance did not resolve ticker metadata.

    When Google Finance cannot fully resolve the symbol page, the title tends
    to be the plain ``"<TICKER> - Google Finance"`` variant. Those pages still
    contain market widgets (e.g. Dow Jones) and can trick generic extractors
    into returning unrelated prices.
    """

    match = TITLE_RE.search(html)
    if not match:
        return False
    title = unescape(match.group("title")).strip().upper()
    expected = f"{ticker.upper()} - GOOGLE FINANCE"
    return title == expected


def _parse_batchexecute_price(raw_payload: str) -> float:
    """Extract the price value from the ``mKsvE`` RPC payload."""

    try:
        data = json.loads(raw_payload)
        quote_block = data[0][0][3]
        price_block = quote_block[5]
        price = price_block[0]
    except (IndexError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(
            "Estrutura inesperada na resposta da API do Google Finance"
        ) from exc
    if not isinstance(price, (int, float)):
        raise ValueError("Preço ausente na resposta da API do Google Finance")
    return float(price)


def _build_batchexecute_body(symbol: str) -> str:
    """Return the serialized ``f.req`` payload for ``mKsvE``."""

    serialized_symbol = json.dumps([symbol])
    return json.dumps([[['mKsvE', serialized_symbol, None, 'generic']]])


def _fetch_price_from_batchexecute(
    symbol: str,
    source_path: str,
    html: str,
    session: requests.sessions.Session | Any,
) -> float:
    """Use the internal batchexecute endpoint as a fallback source."""

    global_data = _extract_global_data(html)
    if not global_data:
        raise ValueError('window.WIZ_global_data ausente')

    build_label = str(global_data.get('cfb2h') or DEFAULT_BUILD_LABEL)
    lang = _detect_page_language(html)
    params = {
        'rpcids': 'mKsvE',
        'source-path': source_path,
        'hl': lang or DEFAULT_LANG,
        'bl': build_label or DEFAULT_BUILD_LABEL,
        'rt': 'c',
    }
    f_sid = global_data.get('FdrFJe')
    if f_sid:
        params['f.sid'] = str(f_sid)

    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'Referer': f'https://www.google.com{source_path}',
    }
    body = {'f.req': _build_batchexecute_body(symbol)}

    response = session.post(
        'https://www.google.com/finance/_/GoogleFinanceUi/data/batchexecute',
        params=params,
        data=body,
        headers=headers,
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    payload = _extract_wrapped_rpc_payload(response.text, 'mKsvE')
    if not payload:
        raise ValueError('Resposta da API não trouxe o payload esperado')
    return _parse_batchexecute_price(payload)


def fetch_google_finance_price(
    ticker: str,
    exchange: str = "BVMF",
    session: Optional[requests.Session] = None,
) -> float:
    """Fetch the latest price for ``ticker`` from Google Finance."""

    ticker_upper = ticker.upper()
    if ticker_upper == "IBOV":
        symbol = "IBOV:INDEXBVMF"
    else:
        symbol = f"{ticker_upper}:{exchange}"

    url = f"https://www.google.com/finance/quote/{symbol}"
    source_path = f"/finance/quote/{symbol}"

    logger.warning("Fetching Google Finance URL %s for ticker %s", url, ticker)
    sess = session or requests
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = sess.get(url, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as exc:  # pragma: no cover - network error
        status = getattr(getattr(exc, "response", None), "status_code", None)
        text_excerpt = getattr(getattr(exc, "response", None), "text", "")
        raise GoogleFinancePriceError(
            ticker,
            f"Falha ao requisitar preço para {ticker}: {exc}",
            url=url,
            status=status,
            cause=exc,
            response_excerpt=_normalize_excerpt(text_excerpt) if text_excerpt else None,
        ) from exc

    logger.warning(
        "Received response with status %s for ticker %s",
        response.status_code,
        ticker,
    )

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise GoogleFinancePriceError(
            ticker,
            f"Resposta HTTP {response.status_code} para {ticker}",
            url=url,
            status=response.status_code,
            cause=exc,
            response_excerpt=_normalize_excerpt(getattr(response, "text", "")),
        ) from exc

    html = response.text
    if _has_unresolved_ticker_title(html, ticker_upper):
        logger.warning(
            "Google Finance returned unresolved quote page for %s; trying batchexecute fallback",
            ticker,
        )
        try:
            price = _fetch_price_from_batchexecute(symbol, source_path, html, sess)
        except (ValueError, requests.RequestException) as api_error:
            message = (
                f"Google Finance não retornou cotação resolvida para {ticker} "
                f"e o fallback via API falhou: {api_error}"
            )
            raise GoogleFinancePriceError(
                ticker,
                message,
                url=url,
                status=response.status_code,
                cause=api_error,
                response_excerpt=_normalize_excerpt(html),
            ) from api_error
        logger.warning(
            "Extracted price %.2f for ticker %s via unresolved-page fallback",
            price,
            ticker,
        )
        return price

    try:
        price = extract_price_from_html(html)
    except ValueError as html_error:
        logger.warning(
            "HTML parsing failed for %s (%s); trying batchexecute fallback",
            ticker,
            html_error,
        )
        try:
            price = _fetch_price_from_batchexecute(symbol, source_path, html, sess)
        except (ValueError, requests.RequestException) as api_error:
            message = (
                f"Não foi possível extrair o preço para {ticker} "
                f"após o fallback via API: {api_error}"
            )
            raise GoogleFinancePriceError(
                ticker,
                message,
                url=url,
                status=response.status_code,
                cause=api_error,
                response_excerpt=_normalize_excerpt(html),
            ) from api_error
        else:
            logger.warning(
                "Extracted price %.2f for ticker %s via batchexecute fallback",
                price,
                ticker,
            )

    logger.warning("Extracted price %.2f for ticker %s", price, ticker)
    return price
