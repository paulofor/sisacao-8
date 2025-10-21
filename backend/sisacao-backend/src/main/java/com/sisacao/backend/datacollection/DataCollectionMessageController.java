package com.sisacao.backend.datacollection;

import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/data-collections/messages")
public class DataCollectionMessageController {

    private final DataCollectionMessageService service;

    public DataCollectionMessageController(DataCollectionMessageService service) {
        this.service = service;
    }

    @GetMapping
    public List<DataCollectionMessage> listMessages(
            @RequestParam(name = "severity", required = false) String severity,
            @RequestParam(name = "collector", required = false) String collector,
            @RequestParam(name = "limit", required = false) Integer limit) {
        return service.findMessages(severity, collector, limit);
    }
}
