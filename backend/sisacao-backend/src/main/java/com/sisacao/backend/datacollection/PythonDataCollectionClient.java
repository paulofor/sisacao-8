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
import java.nio.file.StandardCopyOption;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.Resource;
import org.springframework.core.io.ResourceLoader;
import org.springframework.stereotype.Component;

@Component
public class PythonDataCollectionClient {

    private static final Logger LOGGER = LoggerFactory.getLogger(PythonDataCollectionClient.class);

    private final ObjectMapper objectMapper;
    private final ResourceLoader resourceLoader;
    private final String pythonExecutable;
    private final Path scriptPath;
    private final Duration timeout;

    public PythonDataCollectionClient(
            ObjectMapper mapper,
            ResourceLoader resourceLoader,
            @Value("${sisacao.data-collection.python-executable:python3}") String pythonExecutable,
            @Value(
                            "${sisacao.data-collection.python-script:classpath:/python/export_collection_messages.py}")
                    String scriptPath,
            @Value("${sisacao.data-collection.python-timeout:PT30S}") Duration timeout) {
        this.objectMapper = mapper.copy().findAndRegisterModules();
        this.resourceLoader = resourceLoader;
        this.pythonExecutable = pythonExecutable;
        this.scriptPath = resolveScriptPath(scriptPath);
        this.timeout = timeout;
    }

    public List<PythonMessage> fetchMessages() {
        if (!Files.exists(scriptPath)) {
            IllegalStateException exception =
                    new IllegalStateException("Python script not found at " + scriptPath.toAbsolutePath());
            LOGGER.error("Unable to execute data collection script: {}", scriptPath, exception);
            throw exception;
        }

        ProcessBuilder processBuilder =
                new ProcessBuilder(pythonExecutable, scriptPath.toString()).redirectErrorStream(true);
        try {
            LOGGER.debug(
                    "Executing data collection script using '{}' at '{}'", pythonExecutable, scriptPath);
            Process process = processBuilder.start();
            String output = readOutput(process.getInputStream());
            boolean finished = process.waitFor(timeout.toMillis(), TimeUnit.MILLISECONDS);
            if (!finished) {
                process.destroyForcibly();
                IllegalStateException exception =
                        new IllegalStateException("Python script execution timed out after " + timeout);
                LOGGER.error("Python data collection script timed out after {}", timeout, exception);
                throw exception;
            }

            int exitCode = process.exitValue();
            if (exitCode != 0) {
                IllegalStateException exception =
                        new IllegalStateException(
                                "Python script exited with status " + exitCode + " and output: " + output);
                LOGGER.error(
                        "Python data collection script exited abnormally with status {} and output: {}",
                        exitCode,
                        output);
                throw exception;
            }

            if (output.isBlank()) {
                LOGGER.debug("Python data collection script returned no messages.");
                return Collections.emptyList();
            }

            List<PythonMessage> messages =
                    objectMapper.readValue(output, new TypeReference<List<PythonMessage>>() {});
            LOGGER.debug("Python data collection script returned {} messages", messages.size());
            return messages;
        } catch (IOException ex) {
            LOGGER.error("I/O failure while executing python data collection script", ex);
            throw new IllegalStateException("Failed to execute python script", ex);
        } catch (InterruptedException ex) {
            Thread.currentThread().interrupt();
            LOGGER.error("Python data collection execution was interrupted", ex);
            throw new IllegalStateException("Failed to execute python script", ex);
        }
    }

    private Path resolveScriptPath(String configuredPath) {
        Path classpathCandidate = tryExtractClasspathResource(configuredPath);
        if (classpathCandidate != null) {
            LOGGER.debug(
                    "Resolved python data collection script '{}' from classpath to '{}'",
                    configuredPath,
                    classpathCandidate);
            return classpathCandidate;
        }

        Path requestedPath = Paths.get(configuredPath);
        LinkedHashSet<Path> candidates = new LinkedHashSet<>();

        String sanitized = stripLeadingParentTraversal(configuredPath);
        if (!sanitized.equals(configuredPath) && !sanitized.isBlank()) {
            Path sanitizedPath = Paths.get(sanitized);
            collectRelativeCandidates(sanitizedPath, candidates);
            candidates.add(Paths.get("/opt/sisacao/app").resolve(sanitizedPath).normalize());
        }

        if (requestedPath.isAbsolute()) {
            candidates.add(requestedPath.normalize());
        } else {
            collectRelativeCandidates(requestedPath, candidates);
            candidates.add(Paths.get("/opt/sisacao/app").resolve(requestedPath).normalize());
        }

        for (Path candidate : candidates) {
            if (Files.exists(candidate)) {
                Path absoluteCandidate = candidate.toAbsolutePath().normalize();
                LOGGER.debug(
                        "Resolved python data collection script '{}' to '{}'",
                        configuredPath,
                        absoluteCandidate);
                return absoluteCandidate;
            }
        }

        if (!sanitized.isBlank()) {
            Path classpathFallback = tryExtractClasspathResource("classpath:/" + sanitized);
            if (classpathFallback != null) {
                LOGGER.debug(
                        "Resolved python data collection script '{}' from classpath fallback to '{}'",
                        configuredPath,
                        classpathFallback);
                return classpathFallback;
            }
        }

        Path fallback = requestedPath.toAbsolutePath().normalize();
        LOGGER.debug(
                "Unable to locate python data collection script '{}' in fallback locations. Using '{}'",
                configuredPath,
                fallback);
        return fallback;
    }

    private Path tryExtractClasspathResource(String configuredPath) {
        if (!configuredPath.startsWith("classpath:")) {
            return null;
        }
        return extractClasspathResource(configuredPath);
    }

    private Path extractClasspathResource(String resourceLocation) {
        Resource resource = resourceLoader.getResource(resourceLocation);
        if (!resource.exists()) {
            return null;
        }
        try (InputStream inputStream = resource.getInputStream()) {
            Path tempFile = Files.createTempFile("sisacao-data-collection-", ".py");
            Files.copy(inputStream, tempFile, StandardCopyOption.REPLACE_EXISTING);
            tempFile.toFile().setExecutable(true);
            tempFile.toFile().deleteOnExit();
            return tempFile.toAbsolutePath().normalize();
        } catch (IOException ex) {
            throw new IllegalStateException(
                    "Failed to load python script from resource '" + resourceLocation + "'", ex);
        }
    }

    private void collectRelativeCandidates(Path relative, Set<Path> candidates) {
        LinkedHashSet<Path> baseDirectories = new LinkedHashSet<>();
        String userDirProperty = System.getProperty("user.dir");
        if (userDirProperty != null && !userDirProperty.isBlank()) {
            baseDirectories.add(Paths.get(userDirProperty).toAbsolutePath());
        }
        baseDirectories.add(Paths.get("").toAbsolutePath());

        for (Path base : baseDirectories) {
            Path current = base;
            while (current != null) {
                candidates.add(current.resolve(relative).normalize());
                current = current.getParent();
            }
        }
    }

    private String stripLeadingParentTraversal(String path) {
        String sanitized = path;
        while (sanitized.startsWith("../") || sanitized.startsWith("..\\")) {
            sanitized = sanitized.substring(3);
        }
        return sanitized;
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
