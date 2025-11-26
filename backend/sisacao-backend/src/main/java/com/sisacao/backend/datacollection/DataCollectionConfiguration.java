package com.sisacao.backend.datacollection;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.cloud.bigquery.BigQuery;
import com.google.cloud.bigquery.BigQueryOptions;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(DataCollectionBigQueryProperties.class)
public class DataCollectionConfiguration {

    @Bean
    @ConditionalOnProperty(prefix = "sisacao.data-collection.bigquery", name = "enabled", havingValue = "true")
    public BigQuery bigQuery(DataCollectionBigQueryProperties properties) {
        BigQueryOptions.Builder builder = BigQueryOptions.newBuilder();
        if (properties.getProjectId() != null && !properties.getProjectId().isBlank()) {
            builder.setProjectId(properties.getProjectId());
        }
        return builder.build().getService();
    }

    @Bean
    @ConditionalOnProperty(prefix = "sisacao.data-collection.bigquery", name = "enabled", havingValue = "true")
    public BigQueryCollectionMessageClient bigQueryCollectionMessageClient(
            BigQuery bigQuery,
            ObjectMapper objectMapper,
            DataCollectionBigQueryProperties properties) {
        return new BigQueryCollectionMessageClient(bigQuery, objectMapper, properties);
    }

    @Bean
    @ConditionalOnProperty(prefix = "sisacao.data-collection.bigquery", name = "enabled", havingValue = "true")
    public BigQueryIntradayMetricsClient bigQueryIntradayMetricsClient(
            BigQuery bigQuery, DataCollectionBigQueryProperties properties) {
        return new BigQueryIntradayMetricsClient(bigQuery, properties);
    }
}
