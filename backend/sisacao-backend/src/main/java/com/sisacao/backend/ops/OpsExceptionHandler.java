package com.sisacao.backend.ops;

import jakarta.servlet.http.HttpServletRequest;
import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice(assignableTypes = OpsController.class)
public class OpsExceptionHandler {

    private static final Logger LOGGER = LoggerFactory.getLogger(OpsExceptionHandler.class);

    @ExceptionHandler(OpsValidationException.class)
    public ResponseEntity<Map<String, Object>> handleValidation(
            OpsValidationException exception, HttpServletRequest request) {
        LOGGER.warn("Erro de validação na Ops API para {}: {}", request.getRequestURI(), exception.getMessage());
        return buildResponse(HttpStatus.BAD_REQUEST, exception.getMessage(), request);
    }

    @ExceptionHandler(OpsDataAccessException.class)
    public ResponseEntity<Map<String, Object>> handleDataAccess(
            OpsDataAccessException exception, HttpServletRequest request) {
        LOGGER.error("Erro de acesso a dados na Ops API para {}", request.getRequestURI(), exception);
        return buildResponse(HttpStatus.BAD_GATEWAY, exception.getMessage(), request);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handleGeneric(Exception exception, HttpServletRequest request) {
        LOGGER.error("Erro inesperado na Ops API para {}", request.getRequestURI(), exception);
        return buildResponse(
                HttpStatus.INTERNAL_SERVER_ERROR,
                "Erro inesperado ao consultar a Ops API.",
                request);
    }

    private ResponseEntity<Map<String, Object>> buildResponse(HttpStatus status, String message, HttpServletRequest request) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("timestamp", OffsetDateTime.now().toString());
        body.put("status", status.value());
        body.put("error", status.getReasonPhrase());
        body.put("message", message);
        body.put("path", request.getRequestURI());
        return ResponseEntity.status(status).body(body);
    }
}
