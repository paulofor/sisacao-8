package com.sisacao.backend.datacollection;

public enum DataCollectionMessageSeverity {
    SUCCESS,
    INFO,
    WARNING,
    ERROR,
    CRITICAL,
    UNKNOWN;

    public static DataCollectionMessageSeverity fromString(String raw) {
        if (raw == null || raw.isBlank()) {
            return UNKNOWN;
        }

        for (DataCollectionMessageSeverity severity : values()) {
            if (severity.name().equalsIgnoreCase(raw)) {
                return severity;
            }
        }

        return UNKNOWN;
    }
}
