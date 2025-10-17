package com.sisacao.backend.logging;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class LogFileService {

    private static final Logger LOGGER = LoggerFactory.getLogger(LogFileService.class);

    private final Path logFilePath;
    private final int defaultLines;
    private final int maxLines;

    public LogFileService(
            @Value("${app.logs.file-path}") String logFilePath,
            @Value("${app.logs.default-lines:200}") int defaultLines,
            @Value("${app.logs.max-lines:1000}") int maxLines) {
        this.logFilePath = Paths.get(logFilePath).toAbsolutePath();
        this.defaultLines = defaultLines;
        this.maxLines = maxLines;
    }

    public int getDefaultLines() {
        return defaultLines;
    }

    public int getMaxLines() {
        return maxLines;
    }

    public String readRecentLines(Integer requestedLines) throws IOException {
        int linesToRead = normalizeLines(requestedLines);
        if (!Files.exists(logFilePath)) {
            LOGGER.warn("Requested log file does not exist at {}", logFilePath);
            throw new NoSuchFileException(logFilePath.toString());
        }

        List<String> lines = Files.readAllLines(logFilePath);
        if (lines.isEmpty()) {
            return "";
        }

        int start = Math.max(lines.size() - linesToRead, 0);
        return lines.subList(start, lines.size()).stream().collect(Collectors.joining(System.lineSeparator()));
    }

    private int normalizeLines(Integer requestedLines) {
        if (requestedLines == null) {
            return defaultLines;
        }

        if (requestedLines <= 0) {
            throw new IllegalArgumentException("lines parameter must be greater than zero");
        }

        return Math.min(requestedLines, maxLines);
    }
}
