# Preparação do backend Spring Boot no Amazon Lightsail

Este guia descreve as etapas para provisionar uma instância Amazon Lightsail, instalar as dependências necessárias e publicar o serviço Spring Boot contido em `backend/sisacao-backend`.

## 1. Provisionamento da instância

1. Acesse o console do Amazon Lightsail e clique em **Create instance**.
2. Escolha a região mais próxima dos usuários alvo e selecione a imagem **Linux/Unix → Ubuntu 22.04 LTS**.
3. Defina um plano de recursos compatível com a carga esperada (mínimo recomendado: 2 vCPUs, 4 GB RAM).
4. Gere ou selecione uma chave SSH para acesso administrativo.
5. Nomeie a instância (ex.: `sisacao-backend-prod`) e conclua a criação.
6. Após a criação, faça o download da chave privada em formato `.pem`. Defina a permissão correta antes de usar:

   ```bash
   chmod 600 ~/Downloads/LightsailDefaultKey-*.pem
   ```

   Opcionalmente, mova a chave para `~/.ssh/sisacao-lightsail.pem` para facilitar o uso futuro.

## 2. Configuração de rede e firewall

1. No painel da instância, abra a aba **Networking**.
2. Garanta que as portas a seguir estejam liberadas no firewall do Lightsail:
   - `22/tcp` para acesso SSH administrativo.
   - `80/tcp` e `443/tcp` para tráfego HTTP/HTTPS.
   - `8080/tcp` apenas se o balanceador/application load balancer externo acessar diretamente o Spring Boot.
3. Opcional: anexe um endereço IP estático para evitar mudança de endpoint após reinicializações.

## 3. Conexão via SSH e preparação do sistema operacional

Conecte-se à instância via SSH (substitua `IP_DA_INSTANCIA` pelo endereço público informado no console):

```bash
ssh -i ~/.ssh/sisacao-lightsail.pem ubuntu@IP_DA_INSTANCIA
```

Dentro da sessão SSH, execute os comandos abaixo para preparar o ambiente:

```bash
# Atualizar pacotes de sistema
sudo apt update && sudo apt upgrade -y

# Instalar utilitários básicos
sudo apt install -y unzip git ufw

# Instalar o Java 21 (necessário para o projeto Spring Boot)
sudo apt install -y openjdk-21-jdk

# (Opcional) Instalar Maven globalmente caso deseje compilar sem o wrapper
sudo apt install -y maven
```

Verifique a instalação:

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

Clone este repositório para a instância (ou faça deploy do artefato gerado pelo pipeline CI/CD). Substitua `<sua-organizacao>` pelo owner correto:

```bash
sudo -u sisacao -H bash -c '
  cd /opt/sisacao
  git clone https://github.com/<sua-organizacao>/sisacao-8.git repo
'
```

Quando precisar atualizar manualmente o código, execute:

```bash
ssh -i ~/.ssh/sisacao-lightsail.pem ubuntu@IP_DA_INSTANCIA \
  "sudo -u sisacao -H bash -c 'cd /opt/sisacao/repo && git fetch --all && git reset --hard origin/main'"
```

Atualize o repositório com as credenciais adequadas (HTTPS com token ou SSH) conforme a política da equipe.

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
sudo -u sisacao cp target/sisacao-backend-0.0.1-SNAPSHOT.jar /opt/sisacao/app/sisacao-backend.jar
```

Para publicar uma nova versão manualmente em uma máquina local, faça o build e copie o artefato via `scp`:

```bash
./mvnw clean package -DskipTests
scp -i ~/.ssh/sisacao-lightsail.pem \
  target/sisacao-backend-0.0.1-SNAPSHOT.jar \
  ubuntu@IP_DA_INSTANCIA:/opt/sisacao/app/sisacao-backend.jar
ssh -i ~/.ssh/sisacao-lightsail.pem ubuntu@IP_DA_INSTANCIA "sudo systemctl restart sisacao-backend.service"
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

## 9. Deploy automatizado via GitHub Actions

Para automatizar a publicação do backend, utilize o pipeline no GitHub (`.github/workflows/deploy.yml`). A seguir está um exemplo de configuração que compila o artefato e envia o JAR para a instância via SSH. Ajuste os nomes de variáveis e caminhos conforme necessário:

```yaml
name: Deploy Backend

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Configurar Java
        uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "21"

      - name: Build do backend
        working-directory: backend/sisacao-backend
        run: ./mvnw clean package -DskipTests

      - name: Enviar artefato para Lightsail
        uses: appleboy/scp-action@v0.1.7
        with:
          host: ${{ secrets.LIGHTSAIL_HOST }}
          username: ubuntu
          key: ${{ secrets.LIGHTSAIL_SSH_KEY }}
          source: backend/sisacao-backend/target/sisacao-backend-0.0.1-SNAPSHOT.jar
          target: /opt/sisacao/app/sisacao-backend.jar
          overwrite: true

      - name: Reiniciar serviço
        uses: appleboy/ssh-action@v0.1.10
        with:
          host: ${{ secrets.LIGHTSAIL_HOST }}
          username: ubuntu
          key: ${{ secrets.LIGHTSAIL_SSH_KEY }}
          script: |
            sudo systemctl restart sisacao-backend.service
            sudo systemctl status sisacao-backend.service --no-pager
```

Crie os seguintes **GitHub Secrets** no repositório:

| Nome                 | Descrição                                                                 |
|----------------------|---------------------------------------------------------------------------|
| `LIGHTSAIL_HOST`     | IP público ou hostname da instância Lightsail.                             |
| `LIGHTSAIL_SSH_KEY`  | Conteúdo da chave privada `.pem` usada para acessar a instância (formato PEM). |
| `LIGHTSAIL_USER` (op) | Usuário SSH (ex.: `ubuntu`). Caso queira parametrizar, ajuste o workflow. |

> O `appleboy/scp-action` substitui o arquivo de destino diretamente. O serviço systemd se encarregará de carregar o novo JAR após o restart.

## 10. Observabilidade e logs

- Utilize `journalctl -u sisacao-backend -f` para acompanhar logs em tempo real.
- Configure alarmes no CloudWatch/Lightsail para monitorar CPU, memória e reinícios do serviço.
- Considere integrar o Actuator com ferramentas de monitoramento (Prometheus/Grafana) expondo métricas em `/actuator/prometheus`.

## 11. Estratégia de atualização

1. Para publicar novas versões manualmente, utilize o procedimento descrito na seção [Build e empacotamento](#7-build-e-empacotamento) ou execute `git pull` seguido do build local.
2. Reinicie o serviço após cada atualização manual:

   ```bash
   sudo systemctl restart sisacao-backend.service
   ```

3. Monitore o status do serviço para verificar o sucesso da atualização:

   ```bash
   sudo systemctl status sisacao-backend.service --no-pager
   journalctl -u sisacao-backend -n 200 --no-pager
   ```

4. Utilize implantações azuis/verdes ou instâncias secundárias para evitar indisponibilidade prolongada em cenários críticos.

---

Seguindo este manual, o backend Spring Boot ficará pronto para atender requisições a partir do Amazon Lightsail com práticas básicas de segurança e operação.
