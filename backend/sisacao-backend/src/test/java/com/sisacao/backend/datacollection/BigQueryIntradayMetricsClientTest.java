package com.sisacao.backend.datacollection;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

import com.google.cloud.bigquery.BigQuery;
import com.google.cloud.bigquery.Field;
import com.google.cloud.bigquery.FieldList;
import com.google.cloud.bigquery.FieldValue;
import com.google.cloud.bigquery.FieldValueList;
import com.google.cloud.bigquery.LegacySQLTypeName;
import com.google.cloud.bigquery.QueryJobConfiguration;
import com.google.cloud.bigquery.TableResult;
import java.time.LocalDate;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

class BigQueryIntradayMetricsClientTest {

    private BigQuery bigQuery;
    private DataCollectionBigQueryProperties properties;

    @BeforeEach
    void setUp() {
        bigQuery = mock(BigQuery.class);
        properties = new DataCollectionBigQueryProperties();
        properties.setDailyDataset("cotacao_intraday");
        properties.setDailyTable("cotacao_ohlcv_diario");
        properties.setDailyDays(2);
    }

    @Test
    void shouldQueryDailyTableUsingDataPregaoColumn() throws Exception {
        TableResult tableResult = mock(TableResult.class);
        FieldValueList newest = row("2024-07-04", 120);
        FieldValueList previous = row("2024-07-03", 118);
        doReturn(List.of(newest, previous)).when(tableResult).iterateAll();
        doReturn(tableResult).when(bigQuery).query(any(QueryJobConfiguration.class));

        BigQueryIntradayMetricsClient client = new BigQueryIntradayMetricsClient(bigQuery, properties);

        List<IntradayDailyCount> counts = client.fetchDailyTableCounts();

        assertThat(counts).hasSize(2);
        assertThat(counts.getFirst().date()).isEqualTo(LocalDate.parse("2024-07-04"));
        assertThat(counts.getFirst().totalRecords()).isEqualTo(120L);
        assertThat(counts.get(1).date()).isEqualTo(LocalDate.parse("2024-07-03"));
        assertThat(counts.get(1).totalRecords()).isEqualTo(118L);

        ArgumentCaptor<QueryJobConfiguration> queryCaptor = ArgumentCaptor.forClass(QueryJobConfiguration.class);
        verify(bigQuery).query(queryCaptor.capture());
        assertThat(queryCaptor.getValue().getQuery()).contains("data_pregao");
    }

    private static FieldValueList row(String date, long totalRecords) {
        return FieldValueList.of(
                List.of(
                        FieldValue.of(FieldValue.Attribute.PRIMITIVE, date),
                        FieldValue.of(FieldValue.Attribute.PRIMITIVE, Long.toString(totalRecords))),
                FieldList.of(
                        Field.of("data_ref", LegacySQLTypeName.DATE),
                        Field.of("total_registros", LegacySQLTypeName.INTEGER)));
    }
}
