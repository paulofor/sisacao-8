#!/usr/bin/env bash
# Script de provisionamento de VPS para deploy do backend Java via SCP.
# Todas as mensagens estão em português conforme solicitado.

set -euo pipefail

# ============================
# Variáveis configuráveis
# ============================
# Nome do usuário que receberá os deploys. Caso já exista, será reaproveitado.
DEPLOY_USER="${DEPLOY_USER:-deploy}"
# Caminho base onde o artefato .jar será publicado.
EMPRESA_SLUG="${EMPRESA_SLUG:-empresa}"
APP_DIR="/opt/${EMPRESA_SLUG}/app"
# Porta SSH utilizada pelo pipeline (padrão 22).
SSH_PORT="${SSH_PORT:-22}"
# Chave pública SSH autorizada para o usuário de deploy. Informe via variável de ambiente.
SSH_PUBLIC_KEY="${SSH_PUBLIC_KEY:-}"
# Versão do Java a instalar. Pode ser alterada conforme necessidade.
JAVA_PACKAGE="${JAVA_PACKAGE:-openjdk-21-jre-headless}"

# Variáveis que serão preenchidas durante a execução para uso no resumo final.
IP_LOCAL=""
IP_PUBLICO=""

# ============================
# Funções auxiliares
# ============================
log() {
    local level="$1"; shift
    printf '[%s] %s\n' "$level" "$*"
}

die() {
    log "ERRO" "$*"
    exit 1
}

requer_root() {
    if [[ "$(id -u)" -ne 0 ]]; then
        die "Execute este script como root (sudo)."
    fi
}

verificar_sistema() {
    if ! command -v apt-get >/dev/null 2>&1; then
        die "Este script foi desenvolvido para distribuições baseadas em Debian/Ubuntu com apt-get."
    fi
}

instalar_pacotes() {
    log "INFO" "Atualizando lista de pacotes..."
    apt-get update -y

    log "INFO" "Instalando pacotes essenciais: ${JAVA_PACKAGE}, openssh-server, ufw, tar, netcat, curl..."
    apt-get install -y "${JAVA_PACKAGE}" openssh-server ufw tar netcat-openbsd curl
}

configurar_ssh() {
    log "INFO" "Habilitando e iniciando o serviço SSH..."
    systemctl enable ssh || systemctl enable sshd || true
    systemctl restart ssh || systemctl restart sshd || true

    if [[ -f /etc/ssh/sshd_config ]]; then
        log "INFO" "Garantindo que a porta ${SSH_PORT} esteja configurada..."
        if ! grep -Eq "^Port ${SSH_PORT}$" /etc/ssh/sshd_config; then
            sed -i "s/^#\?Port .*/Port ${SSH_PORT}/" /etc/ssh/sshd_config
        fi
        systemctl restart ssh || systemctl restart sshd || true
    fi
}

configurar_firewall() {
    if command -v ufw >/dev/null 2>&1; then
        log "INFO" "Configurando firewall UFW..."
        ufw allow "${SSH_PORT}/tcp" || true
        ufw allow 80/tcp || true
        ufw allow 443/tcp || true
        yes | ufw enable || true
    else
        log "AVISO" "UFW não disponível; configure o firewall manualmente se necessário."
    fi
}

criar_usuario_deploy() {
    if id "${DEPLOY_USER}" >/dev/null 2>&1; then
        log "INFO" "Usuário ${DEPLOY_USER} já existe; prosseguindo."
    else
        log "INFO" "Criando usuário ${DEPLOY_USER} para receber deploys..."
        useradd -m -s /bin/bash "${DEPLOY_USER}"
    fi

    local ssh_dir="/home/${DEPLOY_USER}/.ssh"
    mkdir -p "${ssh_dir}"
    chmod 700 "${ssh_dir}"

    if [[ -n "${SSH_PUBLIC_KEY}" ]]; then
        log "INFO" "Registrando chave pública em authorized_keys..."
        printf '%s\n' "${SSH_PUBLIC_KEY}" > "${ssh_dir}/authorized_keys"
        chmod 600 "${ssh_dir}/authorized_keys"
        chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${ssh_dir}"
    else
        log "AVISO" "Variável SSH_PUBLIC_KEY não definida. Adicione a chave manualmente em ${ssh_dir}/authorized_keys."
    fi
}

preparar_diretorios() {
    log "INFO" "Criando diretório de aplicação em ${APP_DIR}..."
    mkdir -p "${APP_DIR}"
    chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "/opt/${EMPRESA_SLUG}"

    log "INFO" "Criando diretório temporário para uploads de artefatos..."
    mkdir -p "/opt/${EMPRESA_SLUG}/tmp"
    chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "/opt/${EMPRESA_SLUG}/tmp"
}

verificar_porta_ssh() {
    IP_LOCAL=$(hostname -I | awk '{print $1}')
    log "INFO" "IP detectado da VPS: ${IP_LOCAL}"

    log "INFO" "Testando se a porta ${SSH_PORT} está respondendo localmente..."
    if nc -zv 127.0.0.1 "${SSH_PORT}" >/dev/null 2>&1; then
        log "INFO" "Porta ${SSH_PORT} responde localmente."
    else
        log "ERRO" "Porta ${SSH_PORT} não respondeu localmente. Verifique o serviço SSH e o firewall." && exit 1
    fi

    IP_PUBLICO=$(curl -fsS https://ifconfig.me || echo "N/D")
    if [[ "${IP_PUBLICO}" == "N/D" ]]; then
        log "AVISO" "Não foi possível detectar automaticamente o IP público."
    else
        log "INFO" "IP público detectado: ${IP_PUBLICO}"
    fi
}

exibir_resumo() {
    cat <<RESUMO

Resumo da preparação:
- Usuário de deploy: ${DEPLOY_USER}
- Diretório da aplicação: ${APP_DIR}
- Porta SSH liberada: ${SSH_PORT}
- Pacote Java instalado: ${JAVA_PACKAGE}
- IP local (interface primária): ${IP_LOCAL}
- IP público: ${IP_PUBLICO}

Próximos passos sugeridos:
1. Configure no GitHub Actions os secrets: HOST, USERNAME, KEY (privada) e ajuste o caminho TARGET para ${APP_DIR}/<nome>.jar.
2. Garanta que o IP ${IP_PUBLICO} esteja liberado na origem (GitHub) caso exista firewall externo.
3. Teste a conexão manualmente usando: ssh -i /caminho/para/sua_chave ${DEPLOY_USER}@<host> -p ${SSH_PORT}

RESUMO
}

main() {
    requer_root
    verificar_sistema
    instalar_pacotes
    configurar_ssh
    configurar_firewall
    criar_usuario_deploy
    preparar_diretorios
    verificar_porta_ssh
    exibir_resumo
    log "SUCESSO" "Ambiente pronto para receber deploys via SCP."
}

main "$@"
