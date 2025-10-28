package com.sisacao.backend.datacollection;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.BufferedReader;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.InvalidPathException;
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
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.TimeUnit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;
import org.springframework.core.io.support.PathMatchingResourcePatternResolver;
import org.springframework.stereotype.Component;

@Component
public class PythonDataCollectionClient {

    private static final Logger LOGGER = LoggerFactory.getLogger(PythonDataCollectionClient.class);

    private final ObjectMapper objectMapper;
    private final String pythonExecutable;
    private final Path scriptPath;
    private final Duration timeout;
    private final Path pythonRoot;

    public PythonDataCollectionClient(
            ObjectMapper mapper,
            @Value("${sisacao.data-collection.python-executable:python3}") String pythonExecutable,
            @Value("${sisacao.data-collection.python-script:../../functions/monitoring/export_collection_messages.py}")
                    String scriptPath,
            @Value("${sisacao.data-collection.python-timeout:PT30S}") Duration timeout) {
        this.objectMapper = mapper.copy().findAndRegisterModules();
        this.pythonExecutable = pythonExecutable;
        Path resolvedPath = resolveScriptPath(scriptPath);
        ScriptLocation location = ensureScriptAvailability(scriptPath, resolvedPath);
        this.scriptPath = location.scriptPath();
        this.pythonRoot = location.pythonRoot();
        this.timeout = timeout;
    }

    public List<PythonMessage> fetchMessages() {
        if (!Files.exists(scriptPath)) {
            IllegalStateException exception =
                    new IllegalStateException("Python script not found at " + scriptPath.toAbsolutePath());
            LOGGER.error("Unable to execute data collection script: {}", scriptPath, exception);
            throw exception;
        }

        ProcessBuilder processBuilder = new ProcessBuilder(pythonExecutable, scriptPath.toString());
        if (pythonRoot != null) {
            Map<String, String> environment = processBuilder.environment();
            prependPath(environment, "PYTHONPATH", pythonRoot.toString());
            environment.putIfAbsent("SISACAO_APP_ROOT", pythonRoot.toString());
            environment.putIfAbsent("SISACAO_PROJECT_ROOT", pythonRoot.toString());
        }
        try {
            LOGGER.debug(
                    "Executing data collection script using '{}' at '{}'", pythonExecutable, scriptPath);
            Process process = processBuilder.start();
            CompletableFuture<String> stdoutFuture = readStreamAsync(process.getInputStream());
            CompletableFuture<String> stderrFuture = readStreamAsync(process.getErrorStream());
            boolean finished = process.waitFor(timeout.toMillis(), TimeUnit.MILLISECONDS);
            if (!finished) {
                process.destroyForcibly();
                IllegalStateException exception =
                        new IllegalStateException("Python script execution timed out after " + timeout);
                String stdout = safeJoin(stdoutFuture, "stdout");
                String stderr = safeJoin(stderrFuture, "stderr");
                logScriptStreams(stdout, stderr);
                LOGGER.error("Python data collection script timed out after {}", timeout, exception);
                throw exception;
            }

            int exitCode = process.exitValue();
            String stderr = safeJoin(stderrFuture, "stderr");
            String output = safeJoin(stdoutFuture, "stdout");
            logScriptStreams(output, stderr);
            if (exitCode != 0) {
                IllegalStateException exception =
                        new IllegalStateException(
                                "Python script exited with status "
                                        + exitCode
                                        + " and stdout: "
                                        + output
                                        + appendIfNotBlank("; stderr: ", stderr));
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

    private void logScriptStreams(String stdout, String stderr) {
        if (LOGGER.isDebugEnabled() && !stdout.isBlank()) {
            LOGGER.debug("Python data collection script stdout: {}", stdout);
        }
        if (LOGGER.isDebugEnabled() && !stderr.isBlank()) {
            LOGGER.debug("Python data collection script stderr: {}", stderr);
        }
    }

    private String appendIfNotBlank(String prefix, String value) {
        if (value == null || value.isBlank()) {
            return "";
        }
        return prefix + value;
    }

    private CompletableFuture<String> readStreamAsync(InputStream stream) {
        return CompletableFuture.supplyAsync(
                () -> {
                    try {
                        return readOutput(stream);
                    } catch (IOException ex) {
                        throw new CompletionException(ex);
                    }
                });
    }

    private String safeJoin(CompletableFuture<String> future, String streamName) {
        try {
            return future.join();
        } catch (CompletionException ex) {
            Throwable cause = ex.getCause() != null ? ex.getCause() : ex;
            LOGGER.error("Failed to read python {} stream", streamName, cause);
            throw new IllegalStateException("Failed to read python " + streamName + " stream", cause);
        }
    }

    private Path resolveScriptPath(String configuredPath) {
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

        Path fallback = requestedPath.toAbsolutePath().normalize();
        LOGGER.debug(
                "Unable to locate python data collection script '{}' in fallback locations. Using '{}'",
                configuredPath,
                fallback);
        return fallback;
    }

    private ScriptLocation ensureScriptAvailability(String configuredPath, Path resolvedPath) {
        if (Files.exists(resolvedPath)) {
            Path absolute = resolvedPath.toAbsolutePath().normalize();
            Path root = locateExistingPythonRoot(absolute.getParent());
            return new ScriptLocation(absolute, root);
        }

        String resourcePath = sanitizeResourcePath(configuredPath);
        if (resourcePath != null) {
            try {
                ClassPathResource resource = new ClassPathResource(resourcePath);
                if (resource.exists()) {
                    Path tempDir = Files.createTempDirectory("sisacao-python-env-");
                    tempDir.toFile().deleteOnExit();
                    String fileName = resolveScriptFileName(configuredPath, resourcePath);
                    Path scriptTarget = tempDir.resolve(fileName);
                    try (InputStream stream = resource.getInputStream()) {
                        Files.createDirectories(scriptTarget.getParent());
                        Files.copy(stream, scriptTarget, StandardCopyOption.REPLACE_EXISTING);
                    }
                    scriptTarget.toFile().deleteOnExit();
                    extractBundledPythonPackage(tempDir);
                    Path normalizedScript = scriptTarget.toAbsolutePath().normalize();
                    Path normalizedRoot = tempDir.toAbsolutePath().normalize();
                    LOGGER.info(
                            "Extracted python data collection script '{}' from classpath to '{}'",
                            resourcePath,
                            normalizedScript);
                    return new ScriptLocation(normalizedScript, normalizedRoot);
                }
            } catch (IOException ex) {
                LOGGER.error(
                        "Failed to extract python data collection script '{}' from classpath",
                        resourcePath,
                        ex);
            }
        }

        Path fallback = resolvedPath.toAbsolutePath().normalize();
        Path root = locateExistingPythonRoot(fallback.getParent());
        return new ScriptLocation(fallback, root);
    }

    private String sanitizeResourcePath(String configuredPath) {
        if (configuredPath == null || configuredPath.isBlank()) {
            return null;
        }

        String sanitized = stripLeadingParentTraversal(configuredPath.replace('\\', '/'));
        if (sanitized.startsWith("classpath:")) {
            sanitized = sanitized.substring("classpath:".length());
        }
        while (sanitized.startsWith("/")) {
            sanitized = sanitized.substring(1);
        }

        if (sanitized.isBlank()) {
            return null;
        }

        return sanitized;
    }

    private String resolveScriptFileName(String configuredPath, String resourcePath) {
        String fallback = "export_collection_messages.py";
        for (String candidate : new String[] {configuredPath, resourcePath}) {
            if (candidate == null || candidate.isBlank()) {
                continue;
            }
            try {
                Path fileName = Paths.get(candidate).getFileName();
                if (fileName != null) {
                    return fileName.toString();
                }
            } catch (InvalidPathException ignored) {
                // Fall back to default name
            }
        }
        return fallback;
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

    private Path locateExistingPythonRoot(Path start) {
        Path current = start;
        while (current != null) {
            Path functionsInit = current.resolve("functions").resolve("__init__.py");
            if (Files.exists(functionsInit)) {
                return current.toAbsolutePath().normalize();
            }
            current = current.getParent();
        }

        Path workingDirectory = Paths.get("").toAbsolutePath().normalize();
        Path workingFunctions = workingDirectory.resolve("functions").resolve("__init__.py");
        if (Files.exists(workingFunctions)) {
            return workingDirectory;
        }

        return null;
    }

    private void extractBundledPythonPackage(Path targetRoot) {
        Path functionsRoot = targetRoot.resolve("functions");
        if (Files.exists(functionsRoot.resolve("__init__.py"))) {
            return;
        }

        PathMatchingResourcePatternResolver resolver =
                new PathMatchingResourcePatternResolver(getClass().getClassLoader());
        try {
            Resource[] resources = resolver.getResources("classpath:/functions/**/*");
            int copied = 0;
            for (Resource resource : resources) {
                if (!resource.exists() || !resource.isReadable()) {
                    continue;
                }
                String relative = extractRelativePath(resource);
                if (relative == null || relative.isBlank()) {
                    continue;
                }
                Path destination = functionsRoot.resolve(relative);
                try (InputStream inputStream = resource.getInputStream()) {
                    Files.createDirectories(destination.getParent());
                    Files.copy(inputStream, destination, StandardCopyOption.REPLACE_EXISTING);
                    destination.toFile().deleteOnExit();
                    copied++;
                } catch (FileNotFoundException ignored) {
                    // Some resource resolvers may expose directories which cannot be opened.
                }
            }
            if (copied == 0) {
                LOGGER.warn(
                        "No bundled python resources were copied to temporary directory '{}'",
                        targetRoot.toAbsolutePath().normalize());
            } else {
                LOGGER.info(
                        "Copied {} bundled python resources to temporary directory '{}'",
                        copied,
                        targetRoot.toAbsolutePath().normalize());
            }
        } catch (IOException ex) {
            LOGGER.error("Failed to extract bundled python resources", ex);
        }
    }

    private String extractRelativePath(Resource resource) throws IOException {
        if (resource instanceof ClassPathResource classPathResource) {
            return trimFunctionsPrefix(classPathResource.getPath());
        }
        return trimFunctionsPrefix(resource.getURL().toString());
    }

    private String trimFunctionsPrefix(String path) {
        if (path == null) {
            return null;
        }
        String normalized = path.replace('\\', '/');
        String marker = "!/functions/";
        int index = normalized.indexOf(marker);
        if (index >= 0) {
            return normalized.substring(index + marker.length());
        }
        marker = "/functions/";
        index = normalized.indexOf(marker);
        if (index >= 0) {
            return normalized.substring(index + marker.length());
        }
        if (normalized.startsWith("functions/")) {
            return normalized.substring("functions/".length());
        }
        return null;
    }

    private void prependPath(Map<String, String> environment, String key, String value) {
        if (value == null || value.isBlank()) {
            return;
        }
        String existing = environment.get(key);
        if (existing == null || existing.isBlank()) {
            environment.put(key, value);
            return;
        }
        String pathSeparator = System.getProperty("path.separator", ":");
        if (existing.contains(value)) {
            return;
        }
        environment.put(key, value + pathSeparator + existing);
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
            String lineSeparator = System.lineSeparator();
            while ((line = reader.readLine()) != null) {
                builder.append(line).append(lineSeparator);
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

    private record ScriptLocation(Path scriptPath, Path pythonRoot) {}
}
