package com.sisacao.backend.ops;

public class OpsDataAccessException extends RuntimeException {

    public OpsDataAccessException(String message) {
        super(message);
    }

    public OpsDataAccessException(String message, Throwable cause) {
        super(message, cause);
    }
}
