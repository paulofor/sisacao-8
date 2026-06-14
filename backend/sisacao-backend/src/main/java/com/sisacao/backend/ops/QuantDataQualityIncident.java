package com.sisacao.backend.ops;

import java.time.LocalDate;

public record QuantDataQualityIncident(
        String incidentType,
        String severity,
        String ticker,
        LocalDate incidentDate,
        String recommendation) {}
