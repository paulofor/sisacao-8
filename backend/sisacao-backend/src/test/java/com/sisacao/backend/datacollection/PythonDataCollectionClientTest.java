package com.sisacao.backend.datacollection;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
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
}
