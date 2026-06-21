package com.sisacao.backend.aiadvisor;

public interface AiAdvisorProvider {

    String providerId();

    AiAdvisorResponse requestAdvice(AiAdvisorRequest request);
}
