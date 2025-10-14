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
# IP público IPv4 conhecido. Se informado, é utilizado diretamente no resumo.
PUBLIC_IPV4_OVERRIDE="${PUBLIC_IPV4_OVERRIDE:-}"
# Chave pública SSH autorizada para o usuário de deploy. Informe via variável de ambiente.
# Conteúdo ou caminho da chave pública SSH autorizada para o usuário de deploy.
# - Defina `SSH_PUBLIC_KEY` com o conteúdo completo (ex.: "ssh-ed25519 AAAA... maquina").
# - Ou informe `SSH_PUBLIC_KEY_FILE`/`SSH_PUBLIC_KEY_PATH` apontando para o arquivo `.pub`.
SSH_PUBLIC_KEY="${SSH_PUBLIC_KEY:-}"
SSH_PUBLIC_KEY_FILE="${SSH_PUBLIC_KEY_FILE:-${SSH_PUBLIC_KEY_PATH:-}}"
# Versão do Java a instalar. Pode ser alterada conforme necessidade.
JAVA_PACKAGE="${JAVA_PACKAGE:-openjdk-21-jre-headless}"

# Variáveis que serão preenchidas durante a execução para uso no resumo final.
IP_LOCAL=""
IP_PUBLICO_IPV4=""
IP_PUBLICO_IPV6=""
CHAVE_PUBLICA_STATUS="nao_configurada"
CHAVE_PRIVADA_GERADA=""
CHAVE_PUBLICA_GERADA=""
SUDO_SEM_SENHA_ARQUIVO=""

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

    log "INFO" "Instalando pacotes essenciais: ${JAVA_PACKAGE}, openssh-server, openssh-client, ufw, tar, netcat, curl..."
    apt-get install -y "${JAVA_PACKAGE}" openssh-server openssh-client ufw tar netcat-openbsd curl
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

resolver_chave_publica() {
    local chave="${SSH_PUBLIC_KEY}"
    local arquivo="${SSH_PUBLIC_KEY_FILE}"

    if [[ -n "${arquivo}" ]]; then
        if [[ -f "${arquivo}" ]]; then
            chave=$(tr -d '\r' <"${arquivo}" | head -n 1)
        else
            log "ERRO" "Arquivo da chave pública informado (${arquivo}) não encontrado."
            return 1
        fi
    elif [[ -n "${chave}" && -f "${chave}" ]]; then
        if [[ -r "${chave}" ]]; then
            chave=$(tr -d '\r' <"${chave}" | head -n 1)
        else
            log "ERRO" "Arquivo ${chave} informado em SSH_PUBLIC_KEY não possui permissão de leitura."
            return 1
        fi
    fi

    if [[ -z "${chave}" ]]; then
        log "AVISO" "Nenhuma chave pública foi fornecida via variáveis SSH_PUBLIC_KEY ou SSH_PUBLIC_KEY_FILE."
        return 1
    fi

    chave=$(printf '%s' "${chave}" | tr -d '\r' | head -n 1)

    if [[ "${chave}" != ssh-* && "${chave}" != ecdsa-* && "${chave}" != sk-ssh-* ]]; then
        log "AVISO" "O conteúdo fornecido não parece ser uma chave pública SSH válida (ssh-, ecdsa- ou sk-ssh-)."
    fi

    printf '%s' "${chave}"
    return 0
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

    local chave_resolvida
    if chave_resolvida=$(resolver_chave_publica); then
        log "INFO" "Registrando chave pública em authorized_keys..."
        printf '%s\n' "${chave_resolvida}" > "${ssh_dir}/authorized_keys"
        chmod 600 "${ssh_dir}/authorized_keys"
        chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${ssh_dir}"
        CHAVE_PUBLICA_STATUS="fornecida"
    else
        log "AVISO" "Nenhuma chave pública registrada automaticamente."
        if gerar_chave_deploy "${ssh_dir}"; then
            CHAVE_PUBLICA_STATUS="gerada"
        else
            log "AVISO" "Adicione manualmente em ${ssh_dir}/authorized_keys."
        fi
    fi
}

configurar_sudo_sem_senha() {
    local sudoers_file="/etc/sudoers.d/${DEPLOY_USER}"
    local entry="${DEPLOY_USER} ALL=(ALL) NOPASSWD: /usr/bin/install, /usr/bin/mv, /bin/systemctl"

    log "INFO" "Configurando sudo sem senha para o usuário ${DEPLOY_USER}..."

    printf '%s\n' "${entry}" >"${sudoers_file}"
    chmod 440 "${sudoers_file}"

    if command -v visudo >/dev/null 2>&1; then
        if visudo -cf "${sudoers_file}" >/dev/null 2>&1; then
            log "INFO" "Arquivo ${sudoers_file} validado com sucesso pelo visudo."
        else
            rm -f "${sudoers_file}"
            die "Falha ao validar ${sudoers_file} com visudo. Nenhuma alteração permanente foi aplicada."
        fi
    else
        log "AVISO" "visudo não encontrado; valide manualmente o arquivo ${sudoers_file} se necessário."
    fi

    SUDO_SEM_SENHA_ARQUIVO="${sudoers_file}"
}

preparar_diretorios() {
    log "INFO" "Criando diretório de aplicação em ${APP_DIR}..."
    mkdir -p "${APP_DIR}"
    chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "/opt/${EMPRESA_SLUG}"

    log "INFO" "Criando diretório temporário para uploads de artefatos..."
    mkdir -p "/opt/${EMPRESA_SLUG}/tmp"
    chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "/opt/${EMPRESA_SLUG}/tmp"
}

gerar_chave_deploy() {
    local ssh_dir="$1"
    local chave_privada="${ssh_dir}/id_ed25519"
    local chave_publica="${chave_privada}.pub"

    if [[ -f "${chave_privada}" || -f "${chave_publica}" ]]; then
        log "INFO" "Par de chaves existente detectado em ${ssh_dir}; reutilizando."
    else
        log "INFO" "Gerando par de chaves SSH (ed25519) para o usuário ${DEPLOY_USER}..."
        ssh-keygen -q -t ed25519 -N "" -f "${chave_privada}" >/dev/null 2>&1 || {
            log "ERRO" "Falha ao gerar chave SSH automaticamente."
            return 1
        }
    fi

    if [[ ! -f "${chave_publica}" ]]; then
        log "ERRO" "Arquivo de chave pública ${chave_publica} não encontrado após a geração."
        return 1
    fi

    log "INFO" "Registrando chave pública gerada automaticamente em authorized_keys..."
    cat "${chave_publica}" > "${ssh_dir}/authorized_keys"
    chmod 600 "${ssh_dir}/authorized_keys"
    [[ -f "${chave_privada}" ]] && chmod 600 "${chave_privada}"
    [[ -f "${chave_publica}" ]] && chmod 600 "${chave_publica}"
    chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${ssh_dir}"

    CHAVE_PRIVADA_GERADA="${chave_privada}"
    CHAVE_PUBLICA_GERADA="${chave_publica}"
    return 0
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

    if [[ -n "${PUBLIC_IPV4_OVERRIDE}" ]]; then
        IP_PUBLICO_IPV4="${PUBLIC_IPV4_OVERRIDE}"
        log "INFO" "Utilizando IP público IPv4 informado manualmente: ${IP_PUBLICO_IPV4}"
    else
        IP_PUBLICO_IPV4=$(curl -4 -fsS https://ifconfig.me || \
            dig +short myip.opendns.com @resolver1.opendns.com 2>/dev/null || echo "N/D")
        if [[ "${IP_PUBLICO_IPV4}" == "N/D" ]]; then
            log "AVISO" "Não foi possível detectar automaticamente o IP público IPv4."
        else
            log "INFO" "IP público IPv4 detectado: ${IP_PUBLICO_IPV4}"
        fi
    fi

    IP_PUBLICO_IPV6=$(curl -6 -fsS https://ifconfig.me || echo "N/D")
    if [[ "${IP_PUBLICO_IPV6}" == "N/D" ]]; then
        log "AVISO" "Não foi possível detectar automaticamente o IP público IPv6."
    else
        log "INFO" "IP público IPv6 detectado: ${IP_PUBLICO_IPV6}"
    fi
}

exibir_resumo() {
    cat <<RESUMO

Resumo da preparação:
- Usuário de deploy: ${DEPLOY_USER}
- Diretório da aplicação: ${APP_DIR}
- Porta SSH liberada: ${SSH_PORT}
- Pacote Java instalado: ${JAVA_PACKAGE}
- sudo sem senha configurado: ${SUDO_SEM_SENHA_ARQUIVO:-nao_configurado}
- IP local (interface primária): ${IP_LOCAL}
- IP público IPv4: ${IP_PUBLICO_IPV4}
- IP público IPv6: ${IP_PUBLICO_IPV6}
- Status da chave SSH autorizada: $(
    case "${CHAVE_PUBLICA_STATUS}" in
        fornecida)
            printf 'informada via variável de ambiente.'
            ;;
        gerada)
            printf 'gerada automaticamente em %s (privada em %s).' "${CHAVE_PUBLICA_GERADA}" "${CHAVE_PRIVADA_GERADA}"
            ;;
        *)
            printf 'não configurada; adicione manualmente em /home/%s/.ssh/authorized_keys.' "${DEPLOY_USER}"
            ;;
    esac)

Próximos passos sugeridos:
1. Configure no GitHub Actions os secrets: HOST (recomenda-se usar o IPv4), USERNAME, KEY (privada) e ajuste o caminho TARGET para ${APP_DIR}/<nome>.jar.
2. Garanta que os IPs ${IP_PUBLICO_IPV4} e ${IP_PUBLICO_IPV6} estejam liberados na origem (GitHub) caso exista firewall externo.
3. Teste a conexão manualmente usando: ssh -i /caminho/para/sua_chave ${DEPLOY_USER}@<host> -p ${SSH_PORT} (se necessário especifique o IPv4 com ssh -i /caminho/para/sua_chave ${DEPLOY_USER}@${IP_PUBLICO_IPV4} -p ${SSH_PORT}).
$(
    if [[ "${CHAVE_PUBLICA_STATUS}" == "gerada" ]]; then
        cat <<PROXIMO
4. Baixe com segurança o conteúdo da chave privada gerada e cadastre-a como secret (ex.: KEY) no GitHub Actions:
   sudo cat ${CHAVE_PRIVADA_GERADA}
   # Copie o conteúdo exibido e remova-o do servidor se desejar utilizar outro mecanismo seguro de armazenamento.
PROXIMO
    fi
)

RESUMO
}

main() {
    requer_root
    verificar_sistema
    instalar_pacotes
    configurar_ssh
    configurar_firewall
    criar_usuario_deploy
    configurar_sudo_sem_senha
    preparar_diretorios
    verificar_porta_ssh
    exibir_resumo
    log "SUCESSO" "Ambiente pronto para receber deploys via SCP."
}

main "$@"
