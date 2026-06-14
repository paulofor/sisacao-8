package com.sisacao.backend.ops;

import java.time.LocalDate;

public record QuantTickerCoverage(
        String ticker,
        String company,
        Boolean active,
        LocalDate firstDate,
        LocalDate lastDate,
        Long daysWithData,
        Long expectedDays,
        Double coveragePct,
        Double avgFinancialVolume,
        Long invalidPriceDays,
        Long invalidVolumeDays,
        Long duplicateDays,
        String eligibilityStatus) {}
