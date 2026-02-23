package com.sisacao.backend.gcp;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "sisacao.gcp.credentials")
public class GcpCredentialsProperties {

    /**
     * Caminho do arquivo JSON de credenciais (absoluto, relativo ou com prefixo
     * classpath:).
     */
    private String location;

    /**
     * Conteúdo bruto do arquivo JSON de credenciais.
     */
    private String json;

    /**
     * Conteúdo JSON em Base64 (útil para variáveis de ambiente).
     */
    private String base64;

    public String getLocation() {
        return location;
    }

    public void setLocation(String location) {
        this.location = location;
    }

    public String getJson() {
        return json;
    }

    public void setJson(String json) {
        this.json = json;
    }

    public String getBase64() {
        return base64;
    }

    public void setBase64(String base64) {
        this.base64 = base64;
    }
}
