package com.sisacao.backend.datacollection;

import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/data-collections")
public class DataCollectionMessageController {

    private final DataCollectionMessageService service;

    public DataCollectionMessageController(DataCollectionMessageService service) {
        this.service = service;
    }

    @GetMapping("/messages")
    public List<DataCollectionMessage> listMessages(
            @RequestParam(name = "severity", required = false) String severity,
            @RequestParam(name = "collector", required = false) String collector,
            @RequestParam(name = "limit", required = false) Integer limit) {
        return service.findMessages(severity, collector, limit);
    }

    @GetMapping("/intraday-summary")
    public IntradaySummary getIntradaySummary() {
        return service.buildIntradaySummary();
    }

    @GetMapping("/intraday-daily-counts")
    public List<IntradayDailyCount> getIntradayDailyCounts() {
        return service.fetchIntradayDailyCounts();
    }
}
