package com.sisacao.backend.datacollection;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.cloud.bigquery.BigQuery;
import com.google.cloud.bigquery.BigQueryException;
import com.google.cloud.bigquery.Field;
import com.google.cloud.bigquery.FieldList;
import com.google.cloud.bigquery.FieldValue;
import com.google.cloud.bigquery.FieldValueList;
import com.google.cloud.bigquery.QueryJobConfiguration;
import com.google.cloud.bigquery.QueryParameterValue;
import com.google.cloud.bigquery.Schema;
import com.google.cloud.bigquery.StandardSQLTypeName;
import com.google.cloud.bigquery.TableResult;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class BigQueryCollectionMessageClient {

    private static final Logger LOGGER = LoggerFactory.getLogger(BigQueryCollectionMessageClient.class);

    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {};
    private static final List<String> ORDER_COLUMN_CANDIDATES =
            List.of("created_at", "createdAt", "timestamp", "event_timestamp", "eventTimestamp", "inserted_at", "insertedAt");

    private final BigQuery bigQuery;
    private final ObjectMapper objectMapper;
    private final DataCollectionBigQueryProperties properties;
    private volatile String resolvedOrderColumn;

    public BigQueryCollectionMessageClient(
            BigQuery bigQuery, ObjectMapper objectMapper, DataCollectionBigQueryProperties properties) {
        this.bigQuery = bigQuery;
        this.objectMapper = objectMapper.copy().findAndRegisterModules();
        this.properties = properties;
    }

    public List<PythonDataCollectionClient.PythonMessage> fetchMessages() {
        String qualifiedTable = buildQualifiedTableName();
        List<String> orderColumns = buildOrderPreferenceList();
        BigQueryException lastMissingColumnException = null;

        for (String orderColumn : orderColumns) {
            String query = buildMessageQuery(qualifiedTable, orderColumn);
            QueryJobConfiguration configuration =
                    QueryJobConfiguration.newBuilder(query)
                            .addNamedParameter("limit", QueryParameterValue.int64(properties.getMaxRows()))
                            .setUseLegacySql(false)
                            .build();

            try {
                TableResult result = bigQuery.query(configuration);
                if (orderColumn != null && !orderColumn.equals(resolvedOrderColumn)) {
                    resolvedOrderColumn = orderColumn;
                }
                List<PythonDataCollectionClient.PythonMessage> messages = mapMessages(result);
                LOGGER.debug(
                        "Retrieved {} collection messages from BigQuery ordering by {}",
                        messages.size(),
                        orderColumn);
                return messages;
            } catch (BigQueryException ex) {
                if (orderColumn != null && isMissingColumnException(ex, orderColumn)) {
                    lastMissingColumnException = ex;
                    LOGGER.debug(
                            "Column '{}' not found in {}. Trying next fallback column.",
                            orderColumn,
                            qualifiedTable);
                    if (Objects.equals(resolvedOrderColumn, orderColumn)) {
                        resolvedOrderColumn = null;
                    }
                    continue;
                }
                throw new IllegalStateException("Failed to query BigQuery for data collection messages", ex);
            } catch (InterruptedException ex) {
                Thread.currentThread().interrupt();
                throw new IllegalStateException(
                        "Interrupted while querying BigQuery for data collection messages", ex);
            }
        }

        throw new IllegalStateException(
                String.format(
                        "None of the configured timestamp columns %s were found in table %s",
                        ORDER_COLUMN_CANDIDATES,
                        qualifiedTable),
                lastMissingColumnException);
    }

    private List<String> buildOrderPreferenceList() {
        LinkedHashSet<String> preference = new LinkedHashSet<>();
        if (resolvedOrderColumn != null && !resolvedOrderColumn.isBlank()) {
            preference.add(resolvedOrderColumn);
        }
        preference.addAll(ORDER_COLUMN_CANDIDATES);
        return new ArrayList<>(preference);
    }

    private String buildMessageQuery(String qualifiedTable, String orderColumn) {
        StringBuilder builder = new StringBuilder("SELECT * FROM ").append(qualifiedTable);
        if (orderColumn != null && !orderColumn.isBlank()) {
            builder.append(" ORDER BY ").append(orderColumn).append(" DESC");
        }
        builder.append(" LIMIT @limit");
        return builder.toString();
    }

    private List<PythonDataCollectionClient.PythonMessage> mapMessages(TableResult result) {
        Schema schema = result.getSchema();
        FieldList fields = schema != null ? schema.getFields() : FieldList.of();
        Map<String, Field> fieldIndex = indexFields(fields);

        List<PythonDataCollectionClient.PythonMessage> messages = new ArrayList<>();
        for (FieldValueList row : result.iterateAll()) {
            messages.add(toMessage(row, fieldIndex));
        }
        return messages;
    }

    private boolean isMissingColumnException(BigQueryException ex, String column) {
        if (ex == null || column == null || column.isBlank()) {
            return false;
        }
        String message = ex.getMessage();
        if (message == null) {
            return false;
        }
        String normalizedMessage = message.toLowerCase(Locale.ROOT);
        return normalizedMessage.contains("unrecognized name")
                && normalizedMessage.contains(column.toLowerCase(Locale.ROOT));
    }

    private String buildQualifiedTableName() {
        String dataset = Optional.ofNullable(properties.getDataset()).filter(value -> !value.isBlank()).orElse("monitoring");
        String table = Optional.ofNullable(properties.getTable()).filter(value -> !value.isBlank()).orElse("collection_messages");

        String projectId = Optional.ofNullable(properties.getProjectId()).filter(value -> !value.isBlank()).orElse(null);
        if (projectId == null) {
            return String.format("`%s.%s`", dataset, table);
        }
        return String.format("`%s.%s.%s`", projectId, dataset, table);
    }

    private PythonDataCollectionClient.PythonMessage toMessage(
            FieldValueList row, Map<String, Field> fieldIndex) {
        String id = firstNonBlank(row, fieldIndex, "id", "message_id", "messageId", "event_id", "eventId", "insertId");
        if (id == null) {
            id = UUID.randomUUID().toString();
        }

        String collector =
                firstNonBlank(
                        row,
                        fieldIndex,
                        "collector",
                        "collector_id",
                        "collectorId",
                        "source",
                        "functionName",
                        "pipeline");
        if (collector == null) {
            collector = "desconhecido";
        }

        String severityRaw = firstNonBlank(row, fieldIndex, "severity", "status", "level");
        String severity = severityRaw != null ? severityRaw.trim().toUpperCase(Locale.ROOT) : "UNKNOWN";

        String summary =
                firstNonBlank(row, fieldIndex, "summary", "message", "description", "detail", "details");
        if (summary == null) {
            summary = "Mensagem não informada";
        }

        String dataset = firstNonBlank(row, fieldIndex, "dataset", "table", "target_table", "resource");
        if (dataset == null) {
            dataset = "";
        }

        OffsetDateTime createdAt =
                firstTimestamp(
                        row,
                        fieldIndex,
                        "created_at",
                        "createdAt",
                        "timestamp",
                        "event_timestamp",
                        "eventTimestamp",
                        "inserted_at",
                        "insertedAt");
        if (createdAt == null) {
            createdAt = OffsetDateTime.now(ZoneOffset.UTC);
        }

        Map<String, Object> metadata = extractMetadata(row, fieldIndex);

        return new PythonDataCollectionClient.PythonMessage(id, collector, severity, summary, dataset, createdAt, metadata);
    }

    private Map<String, Field> indexFields(FieldList fields) {
        if (fields == null) {
            return Collections.emptyMap();
        }
        Map<String, Field> index = new LinkedHashMap<>();
        for (Field field : fields) {
            index.put(field.getName().toLowerCase(Locale.ROOT), field);
        }
        return index;
    }

    private String firstNonBlank(FieldValueList row, Map<String, Field> index, String... candidates) {
        for (String candidate : candidates) {
            FieldValue value = getFieldValue(row, index, candidate);
            String stringValue = toString(value);
            if (stringValue != null && !stringValue.isBlank()) {
                return stringValue.trim();
            }
        }
        return null;
    }

    private OffsetDateTime firstTimestamp(FieldValueList row, Map<String, Field> index, String... candidates) {
        for (String candidate : candidates) {
            FieldValue value = getFieldValue(row, index, candidate);
            if (value == null || value.isNull()) {
                continue;
            }
            Field field = index.get(candidate.toLowerCase(Locale.ROOT));
            OffsetDateTime timestamp = toTimestamp(value, field);
            if (timestamp != null) {
                return timestamp;
            }
        }
        return null;
    }

    private FieldValue getFieldValue(FieldValueList row, Map<String, Field> index, String name) {
        Field field = index.get(name.toLowerCase(Locale.ROOT));
        if (field == null) {
            return null;
        }
        try {
            return row.get(field.getName());
        } catch (IllegalArgumentException ex) {
            return null;
        }
    }

    private String toString(FieldValue value) {
        if (value == null || value.isNull()) {
            return null;
        }
        try {
            return value.getStringValue();
        } catch (UnsupportedOperationException ex) {
            Object raw = value.getValue();
            return raw != null ? raw.toString() : null;
        }
    }

    private OffsetDateTime toTimestamp(FieldValue value, Field field) {
        if (value == null || value.isNull()) {
            return null;
        }
        if (field != null) {
            StandardSQLTypeName type = field.getType().getStandardType();
            switch (type) {
                case TIMESTAMP:
                    try {
                        return value.getTimestampInstant().atOffset(ZoneOffset.UTC);
                    } catch (UnsupportedOperationException ignored) {
                        // Fall back to string parsing below.
                    }
                    break;
                case DATETIME:
                case DATE:
                case TIME:
                case STRING:
                case JSON:
                    String stringValue = toString(value);
                    return parseTimestamp(stringValue);
                default:
                    break;
            }
        }

        String raw = toString(value);
        return parseTimestamp(raw);
    }

    private OffsetDateTime parseTimestamp(String raw) {
        if (raw == null || raw.isBlank()) {
            return null;
        }
        String trimmed = raw.trim();
        try {
            return OffsetDateTime.parse(trimmed, DateTimeFormatter.ISO_DATE_TIME);
        } catch (DateTimeParseException ignored) {
            // Try ISO instant without offset
        }
        try {
            Instant instant = Instant.parse(trimmed);
            return instant.atOffset(ZoneOffset.UTC);
        } catch (DateTimeParseException ignored) {
            // Not an instant representation
        }
        try {
            long seconds = Long.parseLong(trimmed);
            return Instant.ofEpochSecond(seconds).atOffset(ZoneOffset.UTC);
        } catch (NumberFormatException ignored) {
            // Not a numeric timestamp
        }
        try {
            long micros = Long.parseLong(trimmed);
            long seconds = TimeUnit.MICROSECONDS.toSeconds(micros);
            long nanos = TimeUnit.MICROSECONDS.toNanos(micros % 1_000_000);
            return Instant.ofEpochSecond(seconds, nanos).atOffset(ZoneOffset.UTC);
        } catch (NumberFormatException ignored) {
            // Give up and return null
        }
        return null;
    }

    private Map<String, Object> extractMetadata(FieldValueList row, Map<String, Field> index) {
        Field metadataField = null;
        FieldValue metadataValue = null;
        for (String candidate : List.of("metadata", "meta", "details", "info")) {
            metadataField = index.get(candidate.toLowerCase(Locale.ROOT));
            if (metadataField != null) {
                metadataValue = getFieldValue(row, index, metadataField.getName());
                if (metadataValue != null && !metadataValue.isNull()) {
                    break;
                }
            }
        }

        if (metadataField == null || metadataValue == null || metadataValue.isNull()) {
            return Collections.emptyMap();
        }

        Object converted = convertFieldValue(metadataValue, metadataField);
        if (converted == null) {
            return Collections.emptyMap();
        }

        try {
            return objectMapper.convertValue(converted, MAP_TYPE);
        } catch (IllegalArgumentException ex) {
            LOGGER.debug("Unable to convert metadata value to map: {}", converted, ex);
            return Map.of("raw", converted.toString());
        }
    }

    private Object convertFieldValue(FieldValue value, Field field) {
        if (value == null || value.isNull()) {
            return null;
        }

        StandardSQLTypeName type = field.getType().getStandardType();
        switch (type) {
            case BOOL:
                return value.getBooleanValue();
            case INT64:
                return value.getLongValue();
            case FLOAT64:
                return value.getDoubleValue();
            case NUMERIC:
            case BIGNUMERIC:
                return value.getNumericValue();
            case STRING:
            case BYTES:
            case DATE:
            case TIME:
            case DATETIME:
            case GEOGRAPHY:
            case JSON:
                return toString(value);
            case TIMESTAMP:
                return Optional.ofNullable(toTimestamp(value, field))
                        .map(OffsetDateTime::toString)
                        .orElse(null);
            case STRUCT:
                return convertStruct(value.getRecordValue(), field.getSubFields());
            case ARRAY:
                Field elementField = Field.newBuilder(field.getName(), field.getType(), field.getSubFields()).build();
                return value.getRepeatedValue().stream()
                        .map(element -> convertFieldValue(element, elementField))
                        .collect(Collectors.toList());
            default:
                Object raw = value.getValue();
                if (raw instanceof BigDecimal bigDecimal) {
                    return bigDecimal;
                }
                return raw != null ? raw.toString() : null;
        }
    }

    private Map<String, Object> convertStruct(FieldValueList record, FieldList subFields) {
        if (record == null || subFields == null) {
            return Collections.emptyMap();
        }
        Map<String, Object> map = new LinkedHashMap<>();
        for (int index = 0; index < subFields.size(); index++) {
            Field subField = subFields.get(index);
            FieldValue subValue = record.get(index);
            map.put(subField.getName(), convertFieldValue(subValue, subField));
        }
        return map;
    }
}
