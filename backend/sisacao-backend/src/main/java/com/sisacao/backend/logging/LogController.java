package com.sisacao.backend.logging;

import java.io.IOException;
import java.nio.file.NoSuchFileException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping(path = "/logs", produces = MediaType.TEXT_PLAIN_VALUE)
public class LogController {

    private static final Logger LOGGER = LoggerFactory.getLogger(LogController.class);

    private final LogFileService logFileService;

    public LogController(LogFileService logFileService) {
        this.logFileService = logFileService;
    }

    @GetMapping("/backend")
    public ResponseEntity<String> getBackendLogs(
            @RequestParam(name = "lines", required = false) Integer lines) {
        try {
            String content = logFileService.readRecentLines(lines);
            return ResponseEntity.ok(content);
        } catch (IllegalArgumentException ex) {
            LOGGER.debug("Invalid 'lines' parameter received: {}", lines, ex);
            return ResponseEntity.badRequest().body(ex.getMessage());
        } catch (NoSuchFileException ex) {
            LOGGER.warn("Log file not found when requested through the API", ex);
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                    .body("Log file not found. Has the application generated any logs yet?");
        } catch (IOException ex) {
            LOGGER.error("Failed to read backend log file", ex);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body("Unable to read backend logs. Check server logs for details.");
        }
    }
}
