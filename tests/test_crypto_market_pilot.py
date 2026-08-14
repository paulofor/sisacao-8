from __future__ import annotations

import datetime as dt

import functions.crypto_market_pilot.main as module


def _kline(open_time: int, close_time: int) -> list[object]:
    return [
        open_time,
        "100.0",
        "110.0",
        "90.0",
        "105.0",
        "12.5",
        close_time,
        "1250.0",
        42,
        "7.0",
        "700.0",
        "0",
    ]


def test_parse_closed_klines_normalizes_binance_payload() -> None:
    now = dt.datetime(2026, 8, 14, 12, 2, tzinfo=dt.timezone.utc)
    rows = module._parse_closed_klines(
        symbol="BTCUSDT",
        raw_klines=[_kline(1_786_708_800_000, 1_786_708_859_999)],
        now=now,
        ingested_at=now,
        job_run_id="run-1",
    )

    assert len(rows) == 1
    assert rows[0]["exchange"] == "BINANCE"
    assert rows[0]["base_asset"] == "BTC"
    assert rows[0]["quote_asset"] == "USDT"
    assert rows[0]["trade_count"] == 42
    assert rows[0]["data_quality_flags"] == []


def test_parse_closed_klines_ignores_open_candle() -> None:
    now = dt.datetime(2026, 8, 14, 12, 0, tzinfo=dt.timezone.utc)
    future_close = int((now + dt.timedelta(seconds=59)).timestamp() * 1000)

    rows = module._parse_closed_klines(
        symbol="ETHUSDT",
        raw_klines=[_kline(int(now.timestamp() * 1000), future_close)],
        now=now,
        ingested_at=now,
        job_run_id="run-1",
    )

    assert rows == []


def test_quality_flags_detect_invalid_prices_and_volume() -> None:
    flags = module._quality_flags(
        open_price=100,
        high=95,
        low=90,
        close=101,
        base_volume=-1,
        quote_volume=1,
        trade_count=-1,
    )

    assert flags == [
        "INVALID_OHLC_RANGE",
        "NEGATIVE_VOLUME",
        "NEGATIVE_TRADE_COUNT",
    ]


def test_crypto_market_pilot_dry_run_does_not_initialize_bigquery(monkeypatch) -> None:
    now_ms = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
    monkeypatch.setattr(
        module,
        "_fetch_klines",
        lambda **kwargs: [_kline(now_ms - 120_000, now_ms - 60_001)],
    )

    def fail_client():
        raise AssertionError("BigQuery não deve ser usado em dry_run")

    monkeypatch.setattr(module, "_get_bigquery_client", fail_client)

    response, status = module.crypto_market_pilot(
        {"pairs": ["BTCUSDT", "ETHUSDT"], "limit": 1, "dry_run": True}
    )

    assert status == 200
    assert response["status"] == "ok"
    assert response["row_count"] == 2
    assert response["persisted_count"] == 0


def test_crypto_market_pilot_reports_partial_pair_failure(monkeypatch) -> None:
    now_ms = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)

    def fetch(**kwargs):
        if kwargs["symbol"] == "ETHUSDT":
            raise RuntimeError("exchange unavailable")
        return [_kline(now_ms - 120_000, now_ms - 60_001)]

    monkeypatch.setattr(module, "_fetch_klines", fetch)

    response, status = module.crypto_market_pilot(
        {"pairs": ["BTCUSDT", "ETHUSDT"], "limit": 1, "dry_run": True}
    )

    assert status == 200
    assert response["status"] == "partial"
    assert response["row_count"] == 1
    assert "ETHUSDT" in response["failures"]


def test_normalize_pairs_rejects_invalid_or_excessive_input() -> None:
    assert module._normalize_pairs("btcusdt, ETHUSDT,btcusdt") == (
        "BTCUSDT",
        "ETHUSDT",
    )

    try:
        module._normalize_pairs(["BTC/USDT"])
    except ValueError as exc:
        assert "par inválido" in str(exc)
    else:
        raise AssertionError("par inválido deveria falhar")


def test_merge_rows_loads_staging_merges_and_always_deletes() -> None:
    class Job:
        def result(self):
            return []

    class Client:
        def __init__(self):
            self.created = []
            self.loaded = []
            self.queries = []
            self.deleted = []

        def create_table(self, table):
            self.created.append(table.table_id)
            return table

        def load_table_from_json(self, rows, table_id, job_config=None):
            self.loaded.append((rows, table_id, job_config))
            return Job()

        def query(self, sql):
            self.queries.append(sql)
            return Job()

        def delete_table(self, table_id, not_found_ok=False):
            self.deleted.append((table_id, not_found_ok))

    client = Client()
    rows = [{"symbol": "BTCUSDT"}]

    module._merge_rows(client, rows, "crypto_pilot_test")

    assert len(client.loaded) == 1
    assert len(client.queries) == 1
    assert "MERGE `ingestaokraken.crypto_market.candles_1m`" in client.queries[0]
    assert "target.`event_time` = source.`event_time`" in client.queries[0]
    assert "target.`interval` = source.`interval`" in client.queries[0]
    assert "INSERT (`exchange`, `symbol`, `base_asset`" in client.queries[0]
    assert client.deleted == [
        (
            "ingestaokraken.crypto_market._candles_1m_crypto_pilot_test",
            True,
        )
    ]


def test_ensure_destination_requires_precreated_dataset() -> None:
    class Client:
        def __init__(self):
            self.datasets = []
            self.tables = []

        def get_dataset(self, dataset_id):
            self.datasets.append(dataset_id)
            return object()

        def create_table(self, table, exists_ok=False):
            self.tables.append((table, exists_ok))
            return table

    client = Client()

    module._ensure_destination_table(client)

    assert client.datasets == ["ingestaokraken.crypto_market"]
    assert len(client.tables) == 1
    assert client.tables[0][1] is True
    assert client.tables[0][0].time_partitioning.field == "event_time"
    assert client.tables[0][0].clustering_fields == ["exchange", "symbol"]
