# Preparação do backend Spring Boot no Amazon Lightsail

Este guia descreve as etapas para provisionar uma instância Amazon Lightsail, instalar as dependências necessárias e publicar o serviço Spring Boot contido em `backend/sisacao-backend`.

## 1. Provisionamento da instância

1. Acesse o console do Amazon Lightsail e clique em **Create instance**.
2. Escolha a região mais próxima dos usuários alvo e selecione a imagem **Linux/Unix → Ubuntu 22.04 LTS**.
3. Defina um plano de recursos compatível com a carga esperada (mínimo recomendado: 2 vCPUs, 4 GB RAM).
4. Gere ou selecione uma chave SSH para acesso administrativo.
5. Nomeie a instância (ex.: `sisacao-backend-prod`) e conclua a criação.
6. Anote o **Static IP** (ou configure um IP estático em **Networking → Attach static IP**) para usarmos nas automações de deploy.
   No ambiente atual o IP atribuído é `34.194.252.70`.

## 2. Configuração de rede e firewall

1. No painel da instância, abra a aba **Networking**.
2. Garanta que as portas a seguir estejam liberadas no firewall do Lightsail:
   - `22/tcp` para acesso SSH administrativo.
   - `80/tcp` e `443/tcp` para tráfego HTTP/HTTPS.
   - `8080/tcp` apenas se o balanceador/application load balancer externo acessar diretamente o Spring Boot.
3. Opcional: anexe um endereço IP estático para evitar mudança de endpoint após reinicializações.

## 3. Preparação do sistema operacional

Conecte-se à instância via SSH usando a chave criada no provisionamento e rode os comandos abaixo. Substitua `IP_DA_INSTANCIA` pelo endereço público ou IP estático configurado.

```bash
# Acesso inicial a partir da sua máquina local
ssh -i ~/.ssh/minha-chave-lightsail.pem ubuntu@IP_DA_INSTANCIA

# Atualizar pacotes de sistema
sudo apt update && sudo apt upgrade -y

# Instalar utilitários básicos
sudo apt install -y unzip git ufw curl

# Instalar o Java 21 (necessário para o projeto Spring Boot)
sudo apt install -y openjdk-21-jdk

# (Opcional) Instalar Maven globalmente caso deseje compilar sem o wrapper
sudo apt install -y maven

# Configurar firewall padrão
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 8080/tcp   # Remova esta linha se expuser o backend via proxy reverso
sudo ufw enable
sudo ufw status
```

Verifique a instalação do Java (e do Maven, se instalado):

```bash
java -version
mvn -v  # opcional
```

## 4. Criação de usuário de aplicação

1. Crie um usuário dedicado para executar o serviço, evitando rodar como `root`:

   ```bash
   sudo adduser --system --group --home /opt/sisacao sisacao
   ```

2. Habilite permissões para publicar artefatos no diretório do usuário:

   ```bash
   sudo mkdir -p /opt/sisacao/app
   sudo chown -R sisacao:sisacao /opt/sisacao
   ```

## 5. Obtenção do código fonte

Clone este repositório para a instância (ou faça deploy do artefato gerado pelo pipeline CI/CD). Substitua `ORGANIZACAO` se necessário:

```bash
sudo -u sisacao -H bash -c '
  cd /opt/sisacao
  git clone https://github.com/ORGANIZACAO/sisacao-8.git repo
'
```

Caso a publicação seja via pipeline (recomendado), o repositório local servirá apenas de fallback. Em produção o artefato será enviado automaticamente pelo GitHub Actions (ver seção 10).

## 6. Configuração de variáveis de ambiente

Crie um arquivo `/opt/sisacao/app/.env` (ou utilize o gerenciador de segredos escolhido) com as variáveis necessárias para acesso ao BigQuery e demais integrações:

```bash
GCP_PROJECT=ingestaokraken
BQ_TABLE=ingestaokraken.cotacao_intraday.cotacao_fechamento_diario
GCP_REGION=us-central1
SPRING_PROFILES_ACTIVE=prod
```

Garanta que o arquivo seja acessível apenas pelo usuário da aplicação (`chmod 600`).

## 7. Build e empacotamento

Compile o projeto com o wrapper Maven distribuído no repositório:

```bash
cd /opt/sisacao/repo/backend/sisacao-backend
sudo -u sisacao ./mvnw clean package -DskipTests
cp target/sisacao-backend-0.0.1-SNAPSHOT.jar /opt/sisacao/app/sisacao-backend.jar
```

O artefato pronto para produção ficará em `/opt/sisacao/app/sisacao-backend.jar`.

## 8. Configuração do serviço systemd

Crie o arquivo `/etc/systemd/system/sisacao-backend.service` com o seguinte conteúdo:

```ini
[Unit]
Description=Sisacao Backend Spring Boot
After=network.target

[Service]
User=sisacao
Group=sisacao
EnvironmentFile=/opt/sisacao/app/.env
WorkingDirectory=/opt/sisacao/app
Environment="JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64"
ExecStart=/usr/bin/env bash -c '/usr/bin/java $JAVA_OPTS -jar /opt/sisacao/app/sisacao-backend.jar'
SuccessExitStatus=143
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Recarregue o systemd e habilite o serviço:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sisacao-backend.service
```

## 9. Observabilidade e logs

- Utilize `journalctl -u sisacao-backend -f` para acompanhar logs em tempo real.
- Configure alarmes no CloudWatch/Lightsail para monitorar CPU, memória e reinícios do serviço.
- Considere integrar o Actuator com ferramentas de monitoramento (Prometheus/Grafana) expondo métricas em `/actuator/prometheus`.

## 10. Estratégia de atualização contínua (GitHub → Lightsail)

Para evitar deploys manuais, configure uma esteira no GitHub Actions que constrói e publica o JAR diretamente no Lightsail sempre que houver push na branch principal.

### 10.1 Preparação na instância

1. Gere uma chave SSH exclusiva para o deploy (rodando na instância):

   ```bash
   sudo -u sisacao ssh-keygen -t ed25519 -f /opt/sisacao/.ssh/id_ed25519 -N ""
   sudo -u sisacao cat /opt/sisacao/.ssh/id_ed25519.pub
   ```

2. Adicione o conteúdo do `.pub` ao arquivo `~/.ssh/authorized_keys` do usuário que fará o login (ex.: `ubuntu` ou outro usuário com permissão de `sudo`). Exemplo para o usuário `ubuntu`:

   ```bash
   sudo -u ubuntu mkdir -p /home/ubuntu/.ssh
   sudo bash -c 'cat /opt/sisacao/.ssh/id_ed25519.pub >> /home/ubuntu/.ssh/authorized_keys'
   sudo chmod 700 /home/ubuntu/.ssh
   sudo chmod 600 /home/ubuntu/.ssh/authorized_keys
   ```

3. Liste o fingerprint do host para registrar no GitHub e evitar prompts de confirmação:

   ```bash
   ssh-keyscan IP_DA_INSTANCIA | tee /tmp/lightsail_known_hosts
   cat /tmp/lightsail_known_hosts
   ```

### 10.2 Configuração de segredos no GitHub

No repositório do GitHub, adicione os seguintes segredos em **Settings → Secrets and variables → Actions**:

- `LIGHTSAIL_HOST`: IP ou hostname público da instância.
- `LIGHTSAIL_USER`: Usuário SSH com permissão de sudo (ex.: `ubuntu`).
- `LIGHTSAIL_SSH_KEY`: Conteúdo do `/opt/sisacao/.ssh/id_ed25519` gerado acima.
- `LIGHTSAIL_KNOWN_HOSTS`: Saída do `ssh-keyscan` (para evitar ataques de "man-in-the-middle").

### 10.3 Workflow de deploy automático

Crie (ou adapte) um workflow em `.github/workflows/deploy-lightsail.yml` com o conteúdo base abaixo. Ele será responsável por compilar o backend, transferir o JAR para o servidor e reiniciar o serviço via `systemctl`.

```yaml
name: Deploy backend to Lightsail

on:
  push:
    branches:
      - master
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Java
        uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '21'

      - name: Build backend
        working-directory: backend/sisacao-backend
        run: ./mvnw clean package -DskipTests

      - name: Upload artifact to Lightsail
        uses: appleboy/scp-action@v0.1.7
        with:
          host: ${{ secrets.LIGHTSAIL_HOST }}
          username: ${{ secrets.LIGHTSAIL_USER }}
          key: ${{ secrets.LIGHTSAIL_SSH_KEY }}
          port: 22
          source: backend/sisacao-backend/target/sisacao-backend-0.0.1-SNAPSHOT.jar
          target: /opt/sisacao/app/sisacao-backend.jar
          overwrite: true
          strip_components: 2
          timeout: 120s

      - name: Restart service remotely
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.LIGHTSAIL_HOST }}
          username: ${{ secrets.LIGHTSAIL_USER }}
          key: ${{ secrets.LIGHTSAIL_SSH_KEY }}
          port: 22
          script: |
            sudo systemctl daemon-reload
            sudo systemctl restart sisacao-backend.service
            sudo systemctl status sisacao-backend.service --no-pager
        env:
          SSH_KNOWN_HOSTS: ${{ secrets.LIGHTSAIL_KNOWN_HOSTS }}
```

> **Observação:** O workflow não configura HTTPS porque a aplicação será exposta inicialmente apenas via HTTP na porta 80. Ajustes com `nginx` e certificados TLS podem ser adicionados posteriormente.

### 10.4 Atualização manual (fallback)

Caso o pipeline esteja indisponível, é possível atualizar manualmente realizando `git pull` no diretório `/opt/sisacao/repo` ou enviando o novo JAR via `scp`, seguido do reinício do serviço:

```bash
ssh -i ~/.ssh/minha-chave-lightsail.pem ubuntu@IP_DA_INSTANCIA
sudo systemctl restart sisacao-backend.service
sudo systemctl status sisacao-backend.service --no-pager
```

Para reduzir indisponibilidades, considere manter uma instância secundária pronta para receber o tráfego em deploys futuros (blue/green).

---

Seguindo este manual, o backend Spring Boot ficará pronto para atender requisições a partir do Amazon Lightsail com práticas básicas de segurança e operação.
