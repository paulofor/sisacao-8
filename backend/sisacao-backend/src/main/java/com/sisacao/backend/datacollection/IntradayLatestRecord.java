package com.sisacao.backend.datacollection;

import java.time.OffsetDateTime;

public record IntradayLatestRecord(
        String ticker,
        Double price,
        OffsetDateTime capturedAt,
        String tradeDate,
        String tradeTime) {}
