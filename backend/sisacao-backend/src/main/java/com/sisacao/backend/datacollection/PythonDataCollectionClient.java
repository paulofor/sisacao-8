package com.sisacao.backend.datacollection;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class PythonDataCollectionClient {

    private final ObjectMapper objectMapper;
    private final String pythonExecutable;
    private final Path scriptPath;
    private final Duration timeout;

    public PythonDataCollectionClient(
            ObjectMapper mapper,
            @Value("${sisacao.data-collection.python-executable:python3}") String pythonExecutable,
            @Value("${sisacao.data-collection.python-script:../../functions/monitoring/export_collection_messages.py}")
                    String scriptPath,
            @Value("${sisacao.data-collection.python-timeout:PT30S}") Duration timeout) {
        this.objectMapper = mapper.copy().findAndRegisterModules();
        this.pythonExecutable = pythonExecutable;
        this.scriptPath = Paths.get(scriptPath).toAbsolutePath().normalize();
        this.timeout = timeout;
    }

    public List<PythonMessage> fetchMessages() {
        if (!Files.exists(scriptPath)) {
            throw new IllegalStateException(
                    "Python script not found at " + scriptPath.toAbsolutePath());
        }

        ProcessBuilder processBuilder =
                new ProcessBuilder(pythonExecutable, scriptPath.toString()).redirectErrorStream(true);
        try {
            Process process = processBuilder.start();
            String output = readOutput(process.getInputStream());
            boolean finished = process.waitFor(timeout.toMillis(), TimeUnit.MILLISECONDS);
            if (!finished) {
                process.destroyForcibly();
                throw new IllegalStateException("Python script execution timed out after " + timeout);
            }

            int exitCode = process.exitValue();
            if (exitCode != 0) {
                throw new IllegalStateException(
                        "Python script exited with status " + exitCode + " and output: " + output);
            }

            if (output.isBlank()) {
                return Collections.emptyList();
            }

            return objectMapper.readValue(output, new TypeReference<List<PythonMessage>>() {});
        } catch (IOException ex) {
            throw new IllegalStateException("Failed to execute python script", ex);
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Failed to execute python script", ex);
        }
    }

    private String readOutput(InputStream stream) throws IOException {
        try (BufferedReader reader =
                new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            StringBuilder builder = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                builder.append(line);
            }
            return builder.toString();
        }
    }

    public record PythonMessage(
            String id,
            String collector,
            String severity,
            String summary,
            String dataset,
            OffsetDateTime createdAt,
            Map<String, Object> metadata) {}
}
