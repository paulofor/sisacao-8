package com.sisacao.backend.ops;

import java.time.LocalDate;
import java.time.OffsetDateTime;

public record QuantOperationalDiaryEvent(
        OffsetDateTime eventTimestamp,
        LocalDate eventDate,
        String eventType,
        String strategyId,
        String strategyVersion,
        String ticker,
        String side,
        String eventStatus,
        String eventMessage,
        String operatorNotes) {}
