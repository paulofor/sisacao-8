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
        String qualifiedTable = buildQualifiedIntradayTableName();
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

    public List<IntradayLatestRecord> fetchLatestRecords(int limit) {
        String qualifiedTable = buildQualifiedIntradayTableName();
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

    private String buildQualifiedIntradayTableName() {
        String dataset =
                Optional.ofNullable(properties.getIntradayDataset())
                        .filter(value -> !value.isBlank())
                        .orElse("cotacao_intraday");
        String table =
                Optional.ofNullable(properties.getIntradayTable())
                        .filter(value -> !value.isBlank())
                        .orElse("cotacao_b3");
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
