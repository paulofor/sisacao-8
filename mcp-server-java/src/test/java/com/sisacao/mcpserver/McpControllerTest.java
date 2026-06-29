package com.sisacao.mcpserver;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
class McpControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void shouldInitialize() throws Exception {
        mockMvc.perform(post("/mcp")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
                                """))
                .andExpect(status().isOk())
                .andExpect(header().exists("mcp-session-id"))
                .andExpect(jsonPath("$.result.serverInfo.name").value("sisacao-mcp-java"));
    }

    @Test
    void shouldListTools() throws Exception {
        String sessionId = mockMvc.perform(post("/mcp")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
                                """))
                .andReturn()
                .getResponse()
                .getHeader("mcp-session-id");

        mockMvc.perform(post("/mcp")
                        .contentType(MediaType.APPLICATION_JSON)
                        .header("mcp-session-id", sessionId)
                        .content("""
                                {"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result.tools[0].name").value("ping"))
                .andExpect(jsonPath("$.result.tools[4].name").value("mcp_server_logs"))
                .andExpect(jsonPath("$.result.tools[5].name").value("cloud_run_function_logs"))
                .andExpect(jsonPath("$.result.tools[6].name").value("gcloud_research"))
                .andExpect(jsonPath("$.result.tools[7].name").value("cloud_scheduler_job"))
                .andExpect(jsonPath("$.result.tools[8].name").value("cloud_scheduler_job_write"))
                .andExpect(jsonPath("$.result.tools[9].name").value("neural_evolution_daily_scheduler_apply"));
    }

    @Test
    void shouldCallPingTool() throws Exception {
        String sessionId = mockMvc.perform(post("/mcp")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
                                """))
                .andReturn()
                .getResponse()
                .getHeader("mcp-session-id");

        mockMvc.perform(post("/mcp")
                        .contentType(MediaType.APPLICATION_JSON)
                        .header("mcp-session-id", sessionId)
                        .content("""
                                {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"ping","arguments":{}}}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result.content[0].json.status").value("ok"));
    }

    @Test
    void shouldRejectToolsListWithoutSessionId() throws Exception {
        mockMvc.perform(post("/mcp")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"jsonrpc":"2.0","id":4,"method":"tools/list","params":{}}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.error.code").value(-32001));
    }

    @Test
    void shouldValidateCloudSchedulerWriteAction() throws Exception {
        String sessionId = mockMvc.perform(post("/mcp")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
                                """))
                .andReturn()
                .getResponse()
                .getHeader("mcp-session-id");

        mockMvc.perform(post("/mcp")
                        .contentType(MediaType.APPLICATION_JSON)
                        .header("mcp-session-id", sessionId)
                        .content("""
                                {"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"cloud_scheduler_job_write","arguments":{"action":"invalid","job_name":"neural-evolution-daily"}}}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result.content[0].json.status").value("error"))
                .andExpect(jsonPath("$.result.content[0].json.message").value("action deve ser create, update, pause, resume, run ou delete"));
    }

    @Test
    void shouldRejectMutatingGcloudResearchCommand() throws Exception {
        String sessionId = mockMvc.perform(post("/mcp")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
                                """))
                .andReturn()
                .getResponse()
                .getHeader("mcp-session-id");

        mockMvc.perform(post("/mcp")
                        .contentType(MediaType.APPLICATION_JSON)
                        .header("mcp-session-id", sessionId)
                        .content("""
                                {"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"gcloud_research","arguments":{"args":["scheduler","jobs","update","http","neural-evolution-daily"]}}}
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.result.content[0].json.status").value("error"))
                .andExpect(jsonPath("$.result.content[0].json.message").value("comando gcloud de pesquisa não pode usar verbos mutáveis"));
    }
}
