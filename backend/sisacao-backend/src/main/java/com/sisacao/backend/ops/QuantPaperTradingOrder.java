package com.sisacao.backend.ops;

import java.time.OffsetDateTime;

public record QuantPaperTradingOrder(
        String paperOrderId,
        String strategyId,
        String strategyVersion,
        String ticker,
        String side,
        Long quantity,
        Double expectedEntryPrice,
        Double simulatedEntryPrice,
        Double expectedExitPrice,
        Double simulatedExitPrice,
        Double netPnlPct,
        Double divergencePct,
        String orderStatus,
        String exitReason,
        OffsetDateTime openedAt,
        OffsetDateTime closedAt,
        String notes) {}
