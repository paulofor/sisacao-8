package com.sisacao.backend.ops;

import java.time.LocalDate;
import java.time.OffsetDateTime;

public record Signal(
        LocalDate validFor,
        String ticker,
        String side,
        Double entry,
        Double target,
        Double stop,
        Double score,
        Integer rank,
        OffsetDateTime createdAt) {}
