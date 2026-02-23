package com.sisacao.backend.gcp;

import com.google.auth.Credentials;
import com.google.auth.oauth2.GoogleCredentials;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Base64;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.util.StringUtils;

public class GcpCredentialsProvider {

    private static final Logger LOGGER = LoggerFactory.getLogger(GcpCredentialsProvider.class);
    private static final String CLASSPATH_PREFIX = "classpath:";

    private final GcpCredentialsProperties properties;

    public GcpCredentialsProvider(GcpCredentialsProperties properties) {
        this.properties = properties;
    }

    public Optional<Credentials> getCredentials() {
        if (StringUtils.hasText(properties.getJson())) {
            LOGGER.debug("Carregando credenciais do GCP a partir de JSON bruto fornecido via configuração.");
            return Optional.of(loadFromJson(properties.getJson().trim()));
        }
        if (StringUtils.hasText(properties.getBase64())) {
            LOGGER.debug("Carregando credenciais do GCP a partir de JSON em Base64 fornecido via configuração.");
            return Optional.of(loadFromBase64(properties.getBase64().trim()));
        }
        if (StringUtils.hasText(properties.getLocation())) {
            LOGGER.debug("Carregando credenciais do GCP a partir do caminho {}", properties.getLocation());
            return Optional.of(loadFromLocation(properties.getLocation().trim()));
        }
        LOGGER.debug("Nenhuma credencial específica do GCP foi configurada; serão usadas as Application Default Credentials.");
        return Optional.empty();
    }

    private Credentials loadFromJson(String json) {
        byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
        try (InputStream inputStream = new ByteArrayInputStream(bytes)) {
            return GoogleCredentials.fromStream(inputStream);
        } catch (IOException ex) {
            throw new IllegalStateException("Não foi possível interpretar o JSON fornecido em sisacao.gcp.credentials", ex);
        }
    }

    private Credentials loadFromBase64(String encodedJson) {
        String sanitized = encodedJson == null ? "" : encodedJson.trim();
        sanitized = stripQuotes(sanitized);
        sanitized = sanitized.replaceAll("\\s+", "");
        try {
            byte[] decoded = Base64.getDecoder().decode(sanitized);
            return loadFromJson(new String(decoded, StandardCharsets.UTF_8));
        } catch (IllegalArgumentException ex) {
            throw new IllegalStateException("O valor Base64 configurado em sisacao.gcp.credentials.base64 é inválido.", ex);
        }
    }

    private String stripQuotes(String value) {
        if (value == null) {
            return "";
        }
        if (value.length() >= 2) {
            boolean doubleQuoted = value.startsWith("\"") && value.endsWith("\"");
            boolean singleQuoted = value.startsWith("'") && value.endsWith("'");
            if (doubleQuoted || singleQuoted) {
                return value.substring(1, value.length() - 1);
            }
        }
        return value;
    }

    private Credentials loadFromLocation(String location) {
        if (location.startsWith(CLASSPATH_PREFIX)) {
            String resourcePath = location.substring(CLASSPATH_PREFIX.length());
            InputStream resourceStream =
                    Thread.currentThread().getContextClassLoader().getResourceAsStream(resourcePath);
            if (resourceStream == null) {
                throw new IllegalStateException(
                        "Recurso " + location + " não encontrado no classpath para carregar as credenciais do GCP.");
            }
            try (InputStream inputStream = resourceStream) {
                return GoogleCredentials.fromStream(inputStream);
            } catch (IOException ex) {
                throw new IllegalStateException(
                        "Falha ao ler o recurso " + location + " com as credenciais do GCP.", ex);
            }
        }

        Path path = Path.of(location);
        if (!Files.exists(path)) {
            throw new IllegalStateException(
                    "Arquivo " + location + " não encontrado para carregar as credenciais do GCP.");
        }
        try (InputStream inputStream = Files.newInputStream(path)) {
            return GoogleCredentials.fromStream(inputStream);
        } catch (IOException ex) {
            throw new IllegalStateException(
                    "Falha ao ler o arquivo " + location + " com as credenciais do GCP.", ex);
        }
    }
}
