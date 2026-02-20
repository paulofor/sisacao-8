package com.sisacao.backend.ops;

import java.time.LocalDate;
import java.time.OffsetDateTime;

public record DqCheck(
        LocalDate checkDate,
        String checkName,
        String status,
        String details,
        OffsetDateTime createdAt) {}
