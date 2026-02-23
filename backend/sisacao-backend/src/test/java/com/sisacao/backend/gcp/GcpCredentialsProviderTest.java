package com.sisacao.backend.gcp;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.google.auth.Credentials;
import com.google.auth.oauth2.ServiceAccountCredentials;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.NoSuchAlgorithmException;
import java.util.Base64;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class GcpCredentialsProviderTest {

    private static final String CLIENT_EMAIL = "sa-test@ingestaokraken.iam.gserviceaccount.com";

    @TempDir
    Path tempDir;

    @Test
    void shouldLoadCredentialsFromRawJson() throws Exception {
        String json = buildServiceAccountJson();
        GcpCredentialsProperties properties = new GcpCredentialsProperties();
        properties.setJson(json);

        Credentials credentials = new GcpCredentialsProvider(properties).getCredentials().orElseThrow();

        assertThat(credentials).isInstanceOf(ServiceAccountCredentials.class);
        assertThat(((ServiceAccountCredentials) credentials).getClientEmail()).isEqualTo(CLIENT_EMAIL);
    }

    @Test
    void shouldLoadCredentialsFromBase64() throws Exception {
        String json = buildServiceAccountJson();
        GcpCredentialsProperties properties = new GcpCredentialsProperties();
        properties.setBase64(Base64.getEncoder().encodeToString(json.getBytes(StandardCharsets.UTF_8)));

        Credentials credentials = new GcpCredentialsProvider(properties).getCredentials().orElseThrow();

        assertThat(credentials).isInstanceOf(ServiceAccountCredentials.class);
        assertThat(((ServiceAccountCredentials) credentials).getClientEmail()).isEqualTo(CLIENT_EMAIL);
    }

    @Test
    void shouldLoadCredentialsFromFileLocation() throws Exception {
        String json = buildServiceAccountJson();
        Path credentialsFile = tempDir.resolve("sa.json");
        Files.writeString(credentialsFile, json, StandardCharsets.UTF_8);

        GcpCredentialsProperties properties = new GcpCredentialsProperties();
        properties.setLocation(credentialsFile.toString());

        Credentials credentials = new GcpCredentialsProvider(properties).getCredentials().orElseThrow();

        assertThat(credentials).isInstanceOf(ServiceAccountCredentials.class);
        assertThat(((ServiceAccountCredentials) credentials).getClientEmail()).isEqualTo(CLIENT_EMAIL);
    }

    @Test
    void shouldReturnEmptyWhenNoConfigurationIsProvided() {
        GcpCredentialsProvider provider = new GcpCredentialsProvider(new GcpCredentialsProperties());
        assertThat(provider.getCredentials()).isEmpty();
    }

    @Test
    void shouldFailWhenBase64IsInvalid() {
        GcpCredentialsProperties properties = new GcpCredentialsProperties();
        properties.setBase64("###invalid###");

        GcpCredentialsProvider provider = new GcpCredentialsProvider(properties);

        assertThatThrownBy(provider::getCredentials)
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("Base64");
    }

    @Test
    void shouldFailWhenFileDoesNotExist() {
        GcpCredentialsProperties properties = new GcpCredentialsProperties();
        properties.setLocation(tempDir.resolve("missing.json").toString());

        GcpCredentialsProvider provider = new GcpCredentialsProvider(properties);

        assertThatThrownBy(provider::getCredentials)
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("não encontrado");
    }

    private static String buildServiceAccountJson() throws NoSuchAlgorithmException {
        KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
        generator.initialize(2048);
        KeyPair pair = generator.generateKeyPair();

        String pem = toPem(pair);
        String escapedPem = escapeForJson(pem);

        return """
                {
                  "type": "service_account",
                  "project_id": "ingestaokraken",
                  "private_key_id": "test-key",
                  "private_key": "%s",
                  "client_email": "%s",
                  "client_id": "117581945181881495660",
                  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                  "token_uri": "https://oauth2.googleapis.com/token",
                  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/%s",
                  "universe_domain": "googleapis.com"
                }
                """.formatted(escapedPem, CLIENT_EMAIL, CLIENT_EMAIL.replace("@", "%40"));
    }

    private static String toPem(KeyPair pair) {
        String base64 = Base64.getEncoder().encodeToString(pair.getPrivate().getEncoded());
        StringBuilder builder = new StringBuilder();
        builder.append("-----BEGIN PRIVATE KEY-----\n");
        for (int i = 0; i < base64.length(); i += 64) {
            int end = Math.min(i + 64, base64.length());
            builder.append(base64, i, end).append('\n');
        }
        builder.append("-----END PRIVATE KEY-----\n");
        return builder.toString();
    }

    private static String escapeForJson(String value) {
        return value
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n");
    }
}
