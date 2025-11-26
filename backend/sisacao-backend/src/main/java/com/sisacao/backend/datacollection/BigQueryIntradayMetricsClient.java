package com.sisacao.backend.datacollection;

import com.google.cloud.bigquery.BigQuery;
import com.google.cloud.bigquery.BigQueryException;
import com.google.cloud.bigquery.FieldValue;
import com.google.cloud.bigquery.FieldValueList;
import com.google.cloud.bigquery.QueryJobConfiguration;
import com.google.cloud.bigquery.QueryParameterValue;
import com.google.cloud.bigquery.TableResult;
import java.time.LocalDate;
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

    private String buildQualifiedIntradayTableName() {
        String dataset =
                Optional.ofNullable(properties.getIntradayDataset())
                        .filter(value -> !value.isBlank())
                        .orElse("cotacao_intraday");
        String table =
                Optional.ofNullable(properties.getIntradayTable())
                        .filter(value -> !value.isBlank())
                        .orElse("cotacao_bovespa");
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
}
