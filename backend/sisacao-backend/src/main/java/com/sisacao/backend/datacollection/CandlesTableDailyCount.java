package com.sisacao.backend.datacollection;

import java.time.LocalDate;

public record CandlesTableDailyCount(String tableName, LocalDate date, long totalRecords) {}
