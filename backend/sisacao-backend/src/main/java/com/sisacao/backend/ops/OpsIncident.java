package com.sisacao.backend.ops;

import java.time.LocalDate;
import java.time.OffsetDateTime;

public record OpsIncident(
        String incidentId,
        String checkName,
        LocalDate checkDate,
        String severity,
        String source,
        String summary,
        String status,
        String runId,
        OffsetDateTime createdAt) {}
