package com.sisacao.backend.datacollection;

import com.google.cloud.bigquery.BigQuery;
import com.google.cloud.bigquery.BigQueryException;
import com.google.cloud.bigquery.FieldValue;
import com.google.cloud.bigquery.FieldValueList;
import com.google.cloud.bigquery.QueryJobConfiguration;
import com.google.cloud.bigquery.QueryParameterValue;
import com.google.cloud.bigquery.TableResult;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class BigQueryIntradayMetricsClient {

    private static final Logger LOGGER = LoggerFactory.getLogger(BigQueryIntradayMetricsClient.class);

    private final BigQuery bigQuery;
    private final DataCollectionBigQueryProperties properties;

    public BigQueryIntradayMetricsClient(BigQuery bigQuery, DataCollectionBigQueryProperties properties) {
        this.bigQuery = bigQuery;
        this.properties = properties;
    }

    public List<IntradayDailyCount> fetchDailyCounts() {
        String qualifiedTable = buildQualifiedTableName(properties.getIntradayDataset(), properties.getIntradayTable());
        int lookbackDays = Math.max(properties.getIntradayDays(), 1);

        String query =
                """
                        SELECT
                          DATE(data) AS data_ref,
                          COUNT(*) AS total_registros
                        FROM %s
                        WHERE data >= DATE_SUB(CURRENT_DATE(), INTERVAL @lookbackDays DAY)
                        GROUP BY data_ref
                        ORDER BY data_ref DESC
                        LIMIT @lookbackDays;
                        """
                        .formatted(qualifiedTable);

        QueryJobConfiguration configuration =
                QueryJobConfiguration.newBuilder(query)
                        .addNamedParameter("lookbackDays", QueryParameterValue.int64(lookbackDays))
                        .setUseLegacySql(false)
                        .build();

        try {
            TableResult result = bigQuery.query(configuration);
            List<IntradayDailyCount> counts = new ArrayList<>();
            for (FieldValueList row : result.iterateAll()) {
                LocalDate date = toLocalDate(row.get("data_ref"));
                long totalRecords = toLong(row.get("total_registros"));
                if (date != null) {
                    counts.add(new IntradayDailyCount(date, totalRecords));
                }
            }
            LOGGER.debug("Retrieved {} intraday daily counts from BigQuery", counts.size());
            return counts;
        } catch (BigQueryException ex) {
            throw new IllegalStateException("Failed to query BigQuery for intraday daily counts", ex);
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Interrupted while querying BigQuery for intraday daily counts", ex);
        }
    }

    public List<IntradayDailyCount> fetchDailyTableCounts() {
        String qualifiedTable = buildQualifiedTableName(properties.getDailyDataset(), properties.getDailyTable());
        int tradingSessions = Math.max(properties.getDailyDays(), 1);

        String query =
                """
                        SELECT
                          data_pregao AS data_ref,
                          COUNT(*) AS total_registros
                        FROM %s
                        WHERE data_pregao IS NOT NULL
                        GROUP BY data_pregao
                        ORDER BY data_ref DESC
                        LIMIT @tradingSessions;
                        """
                        .formatted(qualifiedTable);

        QueryJobConfiguration configuration =
                QueryJobConfiguration.newBuilder(query)
                        .addNamedParameter("tradingSessions", QueryParameterValue.int64(tradingSessions))
                        .setUseLegacySql(false)
                        .build();

        try {
            TableResult result = bigQuery.query(configuration);
            List<IntradayDailyCount> counts = new ArrayList<>();
            for (FieldValueList row : result.iterateAll()) {
                LocalDate date = toLocalDate(row.get("data_ref"));
                long totalRecords = toLong(row.get("total_registros"));
                if (date != null) {
                    counts.add(new IntradayDailyCount(date, totalRecords));
                }
            }
            LOGGER.debug("Retrieved {} daily table counts from BigQuery", counts.size());
            return counts;
        } catch (BigQueryException ex) {
            throw new IllegalStateException("Failed to query BigQuery for daily table counts", ex);
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Interrupted while querying BigQuery for daily table counts", ex);
        }
    }


    public List<CandlesTableDailyCount> fetchCandlesTableDailyCounts() {
        String dataset = Optional.ofNullable(properties.getCandlesDataset())
                .filter(value -> !value.isBlank())
                .orElse("cotacao_intraday");
        int lookbackDays = Math.max(properties.getCandlesDays(), 1);

        String candlesDailyTable = buildQualifiedTableName(dataset, properties.getCandlesDailyTable());
        String candlesIntraday15mTable = buildQualifiedTableName(dataset, properties.getCandlesIntraday15mTable());
        String candlesIntraday1hTable = buildQualifiedTableName(dataset, properties.getCandlesIntraday1hTable());

        String query =
                """
                        WITH recent_trading_days AS (
                          SELECT DISTINCT data_pregao AS data_ref
                          FROM %s
                          WHERE data_pregao IS NOT NULL
                          ORDER BY data_ref DESC
                          LIMIT @lookbackDays
                        ),
                        target_tables AS (
                          SELECT 'candles_diarios' AS table_name
                          UNION ALL
                          SELECT 'candles_intraday_15m' AS table_name
                          UNION ALL
                          SELECT 'candles_intraday_1h' AS table_name
                        ),
                        table_counts AS (
                          SELECT 'candles_diarios' AS table_name, data_pregao AS data_ref, COUNT(*) AS total_registros
                          FROM %s
                          WHERE data_pregao IN (SELECT data_ref FROM recent_trading_days)
                          GROUP BY data_ref

                          UNION ALL

                          SELECT 'candles_intraday_15m' AS table_name, reference_date AS data_ref, COUNT(*) AS total_registros
                          FROM %s
                          WHERE reference_date IN (SELECT data_ref FROM recent_trading_days)
                          GROUP BY data_ref

                          UNION ALL

                          SELECT 'candles_intraday_1h' AS table_name, reference_date AS data_ref, COUNT(*) AS total_registros
                          FROM %s
                          WHERE reference_date IN (SELECT data_ref FROM recent_trading_days)
                          GROUP BY data_ref
                        )
                        SELECT
                          target_tables.table_name,
                          recent_trading_days.data_ref,
                          COALESCE(table_counts.total_registros, 0) AS total_registros
                        FROM target_tables
                        CROSS JOIN recent_trading_days
                        LEFT JOIN table_counts
                          ON table_counts.table_name = target_tables.table_name
                         AND table_counts.data_ref = recent_trading_days.data_ref
                        ORDER BY recent_trading_days.data_ref DESC, target_tables.table_name ASC;
                        """
                        .formatted(candlesDailyTable, candlesDailyTable, candlesIntraday15mTable, candlesIntraday1hTable);

        QueryJobConfiguration configuration =
                QueryJobConfiguration.newBuilder(query)
                        .addNamedParameter("lookbackDays", QueryParameterValue.int64(lookbackDays))
                        .setUseLegacySql(false)
                        .build();

        try {
            TableResult result = bigQuery.query(configuration);
            List<CandlesTableDailyCount> counts = new ArrayList<>();
            for (FieldValueList row : result.iterateAll()) {
                String tableName = toStringValue(row.get("table_name"));
                LocalDate date = toLocalDate(row.get("data_ref"));
                long totalRecords = toLong(row.get("total_registros"));
                if (tableName != null && !tableName.isBlank() && date != null) {
                    counts.add(new CandlesTableDailyCount(tableName, date, totalRecords));
                }
            }
            LOGGER.debug("Retrieved {} candles table daily counts from BigQuery", counts.size());
            return counts;
        } catch (BigQueryException ex) {
            throw new IllegalStateException("Failed to query BigQuery for candles table daily counts", ex);
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Interrupted while querying BigQuery for candles table daily counts", ex);
        }
    }

    public List<IntradayLatestRecord> fetchLatestRecords(int limit) {
        String qualifiedTable = buildQualifiedTableName(properties.getIntradayDataset(), properties.getIntradayTable());
        int safeLimit = Math.max(limit, 1);

        String query =
                """
                        SELECT
                          ticker,
                          SAFE_CAST(valor AS FLOAT64) AS valor,
                          CAST(data AS STRING) AS data_ref,
                          CAST(hora AS STRING) AS hora_ref,
                          COALESCE(
                            CAST(data_hora_atual AS TIMESTAMP),
                            TIMESTAMP(DATETIME(data, hora_atual)),
                            TIMESTAMP(DATETIME(data, hora))
                          ) AS captured_at
                        FROM %s
                        ORDER BY captured_at DESC
                        LIMIT @limit;
                        """
                        .formatted(qualifiedTable);

        QueryJobConfiguration configuration =
                QueryJobConfiguration.newBuilder(query)
                        .addNamedParameter("limit", QueryParameterValue.int64(safeLimit))
                        .setUseLegacySql(false)
                        .build();

        try {
            TableResult result = bigQuery.query(configuration);
            List<IntradayLatestRecord> records = new ArrayList<>();
            for (FieldValueList row : result.iterateAll()) {
                records.add(new IntradayLatestRecord(
                        toStringValue(row.get("ticker")),
                        toDouble(row.get("valor")),
                        toOffsetDateTime(row.get("captured_at")),
                        toStringValue(row.get("data_ref")),
                        toStringValue(row.get("hora_ref"))));
            }
            return records;
        } catch (BigQueryException ex) {
            throw new IllegalStateException("Failed to query BigQuery for latest intraday records", ex);
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Interrupted while querying BigQuery for latest intraday records", ex);
        }
    }

    private String buildQualifiedTableName(String configuredDataset, String configuredTable) {
        String dataset = Optional.ofNullable(configuredDataset).filter(value -> !value.isBlank()).orElse("cotacao_intraday");
        String table = Optional.ofNullable(configuredTable).filter(value -> !value.isBlank()).orElse("cotacao_b3");
        String projectId =
                Optional.ofNullable(properties.getProjectId()).filter(value -> !value.isBlank()).orElse(null);
        if (projectId == null) {
            return String.format("`%s.%s`", dataset, table);
        }
        return String.format("`%s.%s.%s`", projectId, dataset, table);
    }

    private LocalDate toLocalDate(FieldValue value) {
        if (value == null || value.isNull()) {
            return null;
        }
        try {
            String raw = value.getStringValue();
            if (raw == null || raw.isBlank()) {
                return null;
            }
            return LocalDate.parse(raw, DateTimeFormatter.ISO_DATE);
        } catch (UnsupportedOperationException ex) {
            Object rawValue = value.getValue();
            if (rawValue == null) {
                return null;
            }
            try {
                return LocalDate.parse(rawValue.toString(), DateTimeFormatter.ISO_DATE);
            } catch (DateTimeParseException parseException) {
                LOGGER.debug("Unable to parse date value {} from BigQuery", rawValue, parseException);
                return null;
            }
        } catch (DateTimeParseException ex) {
            LOGGER.debug("Unable to parse date value from BigQuery", ex);
            return null;
        }
    }

    private long toLong(FieldValue value) {
        if (value == null || value.isNull()) {
            return 0L;
        }
        try {
            return value.getLongValue();
        } catch (UnsupportedOperationException ex) {
            Object raw = value.getValue();
            if (raw == null) {
                return 0L;
            }
            try {
                return Long.parseLong(raw.toString());
            } catch (NumberFormatException parseException) {
                LOGGER.debug(
                        "Unable to parse numeric value {} from BigQuery: {}",
                        raw,
                        parseException.getMessage());
                return 0L;
            }
        }
    }

    private Double toDouble(FieldValue value) {
        if (value == null || value.isNull()) {
            return null;
        }
        try {
            return value.getDoubleValue();
        } catch (UnsupportedOperationException ex) {
            Object raw = value.getValue();
            if (raw == null) {
                return null;
            }
            try {
                return Double.parseDouble(raw.toString());
            } catch (NumberFormatException parseException) {
                LOGGER.debug("Unable to parse double value {} from BigQuery", raw, parseException);
                return null;
            }
        }
    }

    private OffsetDateTime toOffsetDateTime(FieldValue value) {
        if (value == null || value.isNull()) {
            return null;
        }
        try {
            return OffsetDateTime.ofInstant(value.getTimestampInstant(), ZoneOffset.UTC);
        } catch (UnsupportedOperationException ex) {
            String raw = toStringValue(value);
            if (raw == null || raw.isBlank()) {
                return null;
            }
            try {
                return OffsetDateTime.parse(raw);
            } catch (DateTimeParseException parseException) {
                LOGGER.debug("Unable to parse timestamp value {} from BigQuery", raw, parseException);
                return null;
            }
        }
    }

    private String toStringValue(FieldValue value) {
        if (value == null || value.isNull()) {
            return null;
        }
        try {
            return value.getStringValue();
        } catch (UnsupportedOperationException ex) {
            Object raw = value.getValue();
            return raw == null ? null : raw.toString();
        }
    }
}
