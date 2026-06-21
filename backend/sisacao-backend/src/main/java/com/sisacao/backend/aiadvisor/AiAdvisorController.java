package com.sisacao.backend.aiadvisor;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/ai/advisor")
@ConditionalOnProperty(prefix = "sisacao.ai-advisor", name = "enabled", havingValue = "true")
public class AiAdvisorController {

    private final AiAdvisorService service;

    public AiAdvisorController(AiAdvisorService service) {
        this.service = service;
    }

    @PostMapping("/recommendations")
    public AiAdvisorResponse requestRecommendations(@RequestBody AiAdvisorRequest request) {
        return service.requestAdvice(request);
    }

    @ExceptionHandler(AiAdvisorValidationException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public AiAdvisorErrorResponse handleValidation(AiAdvisorValidationException exception) {
        return new AiAdvisorErrorResponse(exception.getMessage());
    }
}
