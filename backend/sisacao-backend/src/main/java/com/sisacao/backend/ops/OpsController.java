package com.sisacao.backend.ops;

import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.List;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/ops")
@ConditionalOnProperty(prefix = "sisacao.ops.bigquery", name = "enabled", havingValue = "true")
public class OpsController {

    private final OpsService opsService;

    public OpsController(OpsService opsService) {
        this.opsService = opsService;
    }

    @GetMapping("/overview")
    public OpsOverview getOverview() {
        return opsService.getOverview();
    }

    @GetMapping("/pipeline")
    public List<PipelineJobStatus> getPipelineStatus() {
        return opsService.getPipelineStatus();
    }

    @GetMapping("/dq/latest")
    public List<DqCheck> getLatestDqChecks() {
        return opsService.getLatestDqChecks();
    }

    @GetMapping("/incidents/open")
    public List<OpsIncident> getOpenIncidents() {
        return opsService.getOpenIncidents();
    }

    @GetMapping("/signals/next")
    public List<Signal> getNextSignals() {
        return opsService.getNextSignals();
    }

    @GetMapping("/signals/history")
    public List<SignalHistoryEntry> getSignalsHistory(
            @RequestParam("from") String from,
            @RequestParam("to") String to,
            @RequestParam(name = "limit", required = false) Integer limit) {
        LocalDate fromDate = parseDate(from, "from");
        LocalDate toDate = parseDate(to, "to");
        return opsService.getSignalsHistory(fromDate, toDate, limit);
    }

    private LocalDate parseDate(String raw, String paramName) {
        if (raw == null || raw.isBlank()) {
            throw new OpsValidationException("O parâmetro '" + paramName + "' é obrigatório e deve estar no formato YYYY-MM-DD.");
        }
        try {
            return LocalDate.parse(raw.trim());
        } catch (DateTimeParseException ex) {
            throw new OpsValidationException(
                    "Não foi possível interpretar o parâmetro '" + paramName + "'. Use o formato YYYY-MM-DD.");
        }
    }
}
