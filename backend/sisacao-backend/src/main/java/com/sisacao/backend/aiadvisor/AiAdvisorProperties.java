package com.sisacao.backend.aiadvisor;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "sisacao.ai-advisor")
public class AiAdvisorProperties {

    private boolean enabled = false;
    private String provider = "noop";
    private int maxCandidates = 10;
    private String geminiApiKey = "";
    private String geminiApiKeyFile = "";
    private String geminiModel = "gemini-1.5-flash";
    private String geminiEndpoint = "https://generativelanguage.googleapis.com";
    private int geminiTimeoutSeconds = 30;

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public String getProvider() {
        return provider;
    }

    public void setProvider(String provider) {
        this.provider = provider;
    }

    public int getMaxCandidates() {
        return maxCandidates;
    }

    public void setMaxCandidates(int maxCandidates) {
        this.maxCandidates = maxCandidates;
    }

    public String getGeminiApiKey() {
        return geminiApiKey;
    }

    public void setGeminiApiKey(String geminiApiKey) {
        this.geminiApiKey = geminiApiKey;
    }

    public String getGeminiApiKeyFile() {
        return geminiApiKeyFile;
    }

    public void setGeminiApiKeyFile(String geminiApiKeyFile) {
        this.geminiApiKeyFile = geminiApiKeyFile;
    }

    public String getGeminiModel() {
        return geminiModel;
    }

    public void setGeminiModel(String geminiModel) {
        this.geminiModel = geminiModel;
    }

    public String getGeminiEndpoint() {
        return geminiEndpoint;
    }

    public void setGeminiEndpoint(String geminiEndpoint) {
        this.geminiEndpoint = geminiEndpoint;
    }

    public int getGeminiTimeoutSeconds() {
        return geminiTimeoutSeconds;
    }

    public void setGeminiTimeoutSeconds(int geminiTimeoutSeconds) {
        this.geminiTimeoutSeconds = geminiTimeoutSeconds;
    }
}
