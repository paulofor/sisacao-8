package com.sisacao.backend.datacollection;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonInclude.Include;
import java.time.OffsetDateTime;
import java.util.Map;

@JsonInclude(Include.NON_NULL)
public record DataCollectionMessage(
        String id,
        String collector,
        DataCollectionMessageSeverity severity,
        String summary,
        String dataset,
        OffsetDateTime createdAt,
        Map<String, Object> metadata) {}
