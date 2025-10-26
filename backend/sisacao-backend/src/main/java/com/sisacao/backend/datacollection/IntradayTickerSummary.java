package com.sisacao.backend.datacollection;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonInclude.Include;

@JsonInclude(Include.NON_NULL)
public record IntradayTickerSummary(String ticker, Double price, boolean success, String error) {}
