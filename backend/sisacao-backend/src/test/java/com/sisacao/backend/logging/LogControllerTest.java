package com.sisacao.backend.logging;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.equalTo;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest(properties = "app.logs.file-path=${java.io.tmpdir}/sisacao-backend-test.log")
@AutoConfigureMockMvc
class LogControllerTest {

    @Autowired private MockMvc mockMvc;

    @Value("${app.logs.file-path}")
    private String logFileLocation;

    private Path logFilePath;

    @BeforeEach
    void setUp() throws IOException {
        logFilePath = Paths.get(logFileLocation);
        Files.createDirectories(logFilePath.getParent());
        Files.write(logFilePath, List.of("line1", "line2", "line3"));
    }

    @AfterEach
    void tearDown() throws IOException {
        if (Files.exists(logFilePath)) {
            Files.delete(logFilePath);
        }
    }

    @Test
    void shouldReturnRequestedNumberOfLines() throws Exception {
        mockMvc.perform(get("/logs/backend").param("lines", "2"))
                .andExpect(status().isOk())
                .andExpect(content().string(containsString("line2")))
                .andExpect(content().string(containsString("line3")))
                .andExpect(content().string(equalTo("line2" + System.lineSeparator() + "line3")));
    }

    @Test
    void shouldReturnBadRequestWhenLinesIsInvalid() throws Exception {
        mockMvc.perform(get("/logs/backend").param("lines", "0"))
                .andExpect(status().isBadRequest())
                .andExpect(content().string(containsString("greater than zero")));
    }

    @Test
    void shouldReturnDefaultLinesWhenLinesParameterIsMissing() throws Exception {
        String response = mockMvc.perform(get("/logs/backend"))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();

        assertThat(response).isEqualTo(String.join(System.lineSeparator(), "line1", "line2", "line3"));
    }
}
