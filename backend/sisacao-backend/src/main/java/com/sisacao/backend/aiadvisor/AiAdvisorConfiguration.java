package com.sisacao.backend.aiadvisor;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(AiAdvisorProperties.class)
@ConditionalOnProperty(prefix = "sisacao.ai-advisor", name = "enabled", havingValue = "true")
public class AiAdvisorConfiguration {
}
