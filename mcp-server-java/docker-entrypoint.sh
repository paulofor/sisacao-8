#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${GOOGLE_APPLICATION_CREDENTIALS:-}" && -r "${GOOGLE_APPLICATION_CREDENTIALS}" ]]; then
  echo "[entrypoint] Credencial encontrada em ${GOOGLE_APPLICATION_CREDENTIALS}."
  if gcloud auth activate-service-account --key-file="${GOOGLE_APPLICATION_CREDENTIALS}" >/dev/null 2>&1; then
    echo "[entrypoint] Service account ativada com sucesso."
  else
    echo "[entrypoint] Falha ao ativar service account via arquivo JSON." >&2
  fi
else
  echo "[entrypoint] GOOGLE_APPLICATION_CREDENTIALS ausente ou não legível; seguindo sem ativação explícita." >&2
fi

if [[ -n "${GCP_PROJECT:-}" ]]; then
  gcloud config set project "${GCP_PROJECT}" >/dev/null 2>&1 || true
fi

exec java -jar /opt/app/mcp-server-java.jar
