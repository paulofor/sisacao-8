# Provisionamento da VPS

Este diretório contém o script `preparar_vps.sh`, responsável por preparar a instância Linux para receber o deploy do backend Java via GitHub Actions.

## Como usar

1. Faça login na VPS via SSH com um usuário que possua privilégios de `sudo`.
2. Baixe o repositório ou copie apenas o diretório `vps/` para a máquina.
3. Torne o script executável e rode-o como `root`:
   ```bash
   chmod +x preparar_vps.sh
   sudo ./preparar_vps.sh
   ```
4. Caso deseje personalizar o usuário de deploy, porta ou chave pública, exporte as variáveis antes de executar:
   ```bash
   export DEPLOY_USER=deploy
   export EMPRESA_SLUG=nome-da-empresa
   export SSH_PORT=22
   export SSH_PUBLIC_KEY="ssh-ed25519 AAAA... comentario"
   sudo ./preparar_vps.sh
   ```

## O que o script faz

- Atualiza os pacotes do sistema e instala dependências básicas (`openjdk`, `openssh-server`, `ufw`, `tar`, `netcat-openbsd`).
- Garante que o serviço SSH está ativo na porta informada e libera o tráfego no firewall (UFW).
- Cria o usuário de deploy (caso ainda não exista) e registra a chave pública fornecida em `authorized_keys`.
- Cria os diretórios `/opt/<empresa>/app` e `/opt/<empresa>/tmp` com a devida permissão para o usuário de deploy.
- Valida localmente se a porta SSH está respondendo, ajudando a evitar timeouts durante o `scp`.
- Exibe um resumo com próximos passos para finalizar a configuração do pipeline.

## Próximos passos

- Ajuste o pipeline no GitHub Actions para utilizar o mesmo `DEPLOY_USER`, `SSH_PORT` e caminho de destino (`/opt/<empresa>/app/<artefato>.jar`).
- Caso exista firewall externo (cloud provider, Security Groups, etc.), libere a porta 22 para os IPs utilizados pelo GitHub Actions.
- Teste manualmente a conexão antes de rodar o pipeline:
  ```bash
  ssh -i /caminho/para/sua_chave ${DEPLOY_USER}@<host> -p ${SSH_PORT}
  ```

Com essas etapas, o erro de timeout (`dial tcp <host>:22: i/o timeout`) tende a desaparecer, pois o serviço SSH estará operacional, a porta liberada e o usuário de deploy devidamente autorizado.
