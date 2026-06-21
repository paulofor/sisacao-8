package com.sisacao.backend.aiadvisor;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

@Component
@ConditionalOnProperty(prefix = "sisacao.ai-advisor", name = "provider", havingValue = "gemini")
public class GeminiAiAdvisorProvider implements AiAdvisorProvider {

    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {};
    private static final TypeReference<List<AiAdvisorCandidate>> CANDIDATES_TYPE = new TypeReference<>() {};

    private final AiAdvisorProperties properties;
    private final ObjectMapper objectMapper;
    private final HttpClient httpClient;

    public GeminiAiAdvisorProvider(AiAdvisorProperties properties, ObjectMapper objectMapper) {
        this(properties, objectMapper, HttpClient.newHttpClient());
    }

    GeminiAiAdvisorProvider(AiAdvisorProperties properties, ObjectMapper objectMapper, HttpClient httpClient) {
        this.properties = properties;
        this.objectMapper = objectMapper;
        this.httpClient = httpClient;
    }

    @Override
    public String providerId() {
        return "gemini";
    }

    @Override
    public AiAdvisorResponse requestAdvice(AiAdvisorRequest request) {
        String apiKey = readApiKey();
        Map<String, Object> payload = Map.of(
                "contents",
                List.of(Map.of("role", "user", "parts", List.of(Map.of("text", toJson(request))))),
                "generationConfig",
                Map.of(
                        "responseMimeType", "application/json",
                        "responseSchema", request.expectedResponseSchema()));
        HttpRequest httpRequest = HttpRequest.newBuilder(geminiUri(apiKey))
                .timeout(Duration.ofSeconds(properties.getGeminiTimeoutSeconds()))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(toJson(payload), StandardCharsets.UTF_8))
                .build();
        try {
            HttpResponse<String> response = httpClient.send(httpRequest, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() < 200 || response.statusCode() >= 300) {
                throw new AiAdvisorValidationException("Gemini advisor request failed with HTTP " + response.statusCode());
            }
            return parseResponse(request, response.body());
        } catch (IOException exc) {
            throw new AiAdvisorValidationException("Gemini advisor request failed: " + exc.getMessage());
        } catch (InterruptedException exc) {
            Thread.currentThread().interrupt();
            throw new AiAdvisorValidationException("Gemini advisor request interrupted");
        }
    }

    private URI geminiUri(String apiKey) {
        return URI.create(properties.getGeminiEndpoint()
                + "/v1beta/models/"
                + properties.getGeminiModel()
                + ":generateContent?key="
                + apiKey);
    }

    private String readApiKey() {
        String inlineKey = properties.getGeminiApiKey();
        if (StringUtils.hasText(inlineKey)) {
            return inlineKey.trim();
        }
        String keyFile = properties.getGeminiApiKeyFile();
        if (!StringUtils.hasText(keyFile)) {
            throw new AiAdvisorValidationException("GEMINI_API_KEY_FILE or GEMINI_API_KEY is required");
        }
        try {
            return Files.readString(Path.of(keyFile), StandardCharsets.UTF_8).trim();
        } catch (IOException exc) {
            throw new AiAdvisorValidationException("Unable to read GEMINI_API_KEY_FILE: " + keyFile);
        }
    }

    private AiAdvisorResponse parseResponse(AiAdvisorRequest request, String body) throws JsonProcessingException {
        JsonNode root = objectMapper.readTree(body);
        String text = root.path("candidates")
                .path(0)
                .path("content")
                .path("parts")
                .path(0)
                .path("text")
                .asText();
        if (!StringUtils.hasText(text)) {
            throw new AiAdvisorValidationException("Gemini advisor response did not include structured text");
        }
        JsonNode structured = objectMapper.readTree(text);
        List<AiAdvisorCandidate> candidates = structured.has("candidates")
                ? objectMapper.convertValue(structured.get("candidates"), CANDIDATES_TYPE)
                : List.of();
        List<String> rejectionReasons = structured.has("rejectionReasons")
                ? objectMapper.convertValue(structured.get("rejectionReasons"), new TypeReference<List<String>>() {})
                : List.of();
        return new AiAdvisorResponse(
                request.advisorRunId(),
                providerId(),
                properties.getGeminiModel(),
                structured.path("status").asText("accepted"),
                structured.path("rationale").asText("Gemini structured advisor response"),
                candidates,
                rejectionReasons,
                objectMapper.convertValue(root, MAP_TYPE),
                null);
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException exc) {
            throw new AiAdvisorValidationException("Unable to serialize Gemini advisor payload");
        }
    }
}
