package com.sisacao.backend.ops;

import java.time.OffsetDateTime;

public record PipelineJobStatus(
        String jobName,
        OffsetDateTime lastRunAt,
        String lastStatus,
        Long minutesSinceLastRun,
        OffsetDateTime deadlineAt,
        boolean isSilent,
        String lastRunId) {}
