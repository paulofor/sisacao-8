package com.sisacao.backend.datacollection;

import java.time.LocalDate;

public record IntradayDailyCount(LocalDate date, long totalRecords) {}
