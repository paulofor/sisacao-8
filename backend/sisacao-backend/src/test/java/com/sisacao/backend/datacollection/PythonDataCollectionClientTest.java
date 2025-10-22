package com.sisacao.backend.datacollection;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class PythonDataCollectionClientTest {

    @TempDir
    Path tempDir;

    @Test
    void shouldParseMessagesFromPythonScript() throws IOException {
        Path script = tempDir.resolve("messages.py");
        String payload =
                "{"
                        + "\"id\": \"evt-100\", "
                        + "\"collector\": \"test-collector\", "
                        + "\"severity\": \"SUCCESS\", "
                        + "\"summary\": \"ok\", "
                        + "\"dataset\": \"test.dataset\", "
                        + "\"createdAt\": \"2024-01-01T10:00:00Z\", "
                        + "\"metadata\": {\"count\": 2}}";
        String content =
                String.join(
                        "\n",
                        "import json",
                        "import sys",
                        "json.dump([" + payload + "], sys.stdout)");
        Files.writeString(script, content);

        PythonDataCollectionClient client =
                new PythonDataCollectionClient(
                        new ObjectMapper(), "python3", script.toString(), Duration.ofSeconds(5));

        List<PythonDataCollectionClient.PythonMessage> messages = client.fetchMessages();
        assertEquals(1, messages.size());
        PythonDataCollectionClient.PythonMessage message = messages.get(0);
        assertEquals("evt-100", message.id());
        assertEquals("test-collector", message.collector());
        assertEquals("SUCCESS", message.severity());
        assertEquals("ok", message.summary());
        assertEquals("test.dataset", message.dataset());
        assertEquals(OffsetDateTime.parse("2024-01-01T10:00:00Z"), message.createdAt());
        assertNotNull(message.metadata());
        assertEquals(2, ((Number) message.metadata().get("count")).intValue());
    }

    @Test
    void shouldExtractScriptFromClasspathWhenConfigured() throws Exception {
        PythonDataCollectionClient client =
                new PythonDataCollectionClient(
                        new ObjectMapper(),
                        "python3",
                        "classpath:test-scripts/simple_messages.py",
                        Duration.ofSeconds(5));

        Field scriptField = PythonDataCollectionClient.class.getDeclaredField("scriptPath");
        scriptField.setAccessible(true);
        Path resolved = (Path) scriptField.get(client);

        assertTrue(Files.exists(resolved), "extracted script should exist on disk");
        assertTrue(resolved.getFileName().toString().endsWith(".py"));
    }

    @Test
    void shouldResolveScriptPathUsingParentTraversalFallback() throws IOException {
        Path appDir = tempDir.resolve("app");
        Path scriptDir = appDir.resolve("functions/monitoring");
        Files.createDirectories(scriptDir);
        Path script = scriptDir.resolve("export_collection_messages.py");
        String payload =
                "{" +
                        "\"id\": \"evt-200\", " +
                        "\"collector\": \"fallback-collector\", " +
                        "\"severity\": \"INFO\", " +
                        "\"summary\": \"fallback\", " +
                        "\"dataset\": \"fallback.dataset\", " +
                        "\"createdAt\": \"2024-01-02T11:30:00Z\", " +
                        "\"metadata\": {\"count\": 1}}";
        String content =
                String.join(
                        "\n",
                        "import json",
                        "import sys",
                        "json.dump([" + payload + "], sys.stdout)");
        Files.writeString(script, content);

        String originalUserDir = System.getProperty("user.dir");
        System.setProperty("user.dir", appDir.toString());
        try {
            PythonDataCollectionClient client =
                    new PythonDataCollectionClient(
                            new ObjectMapper(),
                            "python3",
                            "../../functions/monitoring/export_collection_messages.py",
                            Duration.ofSeconds(5));

            Field scriptField = PythonDataCollectionClient.class.getDeclaredField("scriptPath");
            scriptField.setAccessible(true);
            Path resolved = (Path) scriptField.get(client);
            assertEquals(script.toAbsolutePath().normalize(), resolved);
        } catch (NoSuchFieldException | IllegalAccessException ex) {
            throw new AssertionError("Unable to inspect resolved script path", ex);
        } finally {
            if (originalUserDir == null) {
                System.clearProperty("user.dir");
            } else {
                System.setProperty("user.dir", originalUserDir);
            }
        }
    }
}
