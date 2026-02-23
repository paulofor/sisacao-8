package com.sisacao.backend.gcp;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(GcpCredentialsProperties.class)
public class GcpCredentialsConfiguration {

    @Bean
    public GcpCredentialsProvider gcpCredentialsProvider(GcpCredentialsProperties properties) {
        return new GcpCredentialsProvider(properties);
    }
}
