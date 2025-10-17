package com.sisacao.backend.datacollection;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.is;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
class DataCollectionMessageControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void shouldReturnAllMessages() throws Exception {
        mockMvc.perform(get("/data-collections/messages"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(5)))
                .andExpect(jsonPath("$[0].id", is("evt-001")))
                .andExpect(jsonPath("$[0].severity", is("SUCCESS")));
    }

    @Test
    void shouldFilterMessagesBySeverityAndCollector() throws Exception {
        mockMvc.perform(get("/data-collections/messages")
                        .param("severity", "warning")
                        .param("collector", "ingestao-crypto"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].id", is("evt-002")))
                .andExpect(jsonPath("$[0].severity", is("WARNING")))
                .andExpect(jsonPath("$[0].collector", is("ingestao-crypto")));
    }

    @Test
    void shouldRespectLimitParameter() throws Exception {
        mockMvc.perform(get("/data-collections/messages").param("limit", "2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(2)))
                .andExpect(jsonPath("$[0].id", is("evt-001")))
                .andExpect(jsonPath("$[1].id", is("evt-002")));
    }

    @Test
    void shouldAllowFrontendOriginViaCors() throws Exception {
        mockMvc.perform(get("/data-collections/messages").header("Origin", "http://localhost:5173"))
                .andExpect(status().isOk())
                .andExpect(header().string("Access-Control-Allow-Origin", "http://localhost:5173"));
    }

    @Test
    void shouldAllowPreflightRequests() throws Exception {
        mockMvc.perform(options("/data-collections/messages")
                        .header("Origin", "http://localhost:5173")
                        .header("Access-Control-Request-Method", "GET"))
                .andExpect(status().isOk())
                .andExpect(header().string("Access-Control-Allow-Origin", "http://localhost:5173"))
                .andExpect(header().string("Access-Control-Allow-Methods", containsString("GET")));
    }
}
