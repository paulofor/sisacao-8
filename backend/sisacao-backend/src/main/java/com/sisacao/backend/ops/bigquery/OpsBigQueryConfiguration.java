package com.sisacao.backend.ops.bigquery;

import com.google.cloud.bigquery.BigQuery;
import com.google.cloud.bigquery.BigQueryOptions;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(OpsBigQueryProperties.class)
public class OpsBigQueryConfiguration {

    @Bean
    @ConditionalOnProperty(prefix = "sisacao.ops.bigquery", name = "enabled", havingValue = "true")
    public BigQueryOpsClient bigQueryOpsClient(
            ObjectProvider<BigQuery> bigQueryProvider, OpsBigQueryProperties properties) {
        BigQuery bigQuery = bigQueryProvider.getIfAvailable(() -> buildBigQuery(properties));
        return new BigQueryOpsClient(bigQuery, properties);
    }

    private BigQuery buildBigQuery(OpsBigQueryProperties properties) {
        BigQueryOptions.Builder builder = BigQueryOptions.newBuilder();
        if (properties.getProjectId() != null && !properties.getProjectId().isBlank()) {
            builder.setProjectId(properties.getProjectId());
        }
        return builder.build().getService();
    }
}
