# Preparação do backend Spring Boot no Amazon Lightsail

Este guia descreve as etapas para provisionar uma instância Amazon Lightsail, instalar as dependências necessárias e publicar o serviço Spring Boot contido em `backend/sisacao-backend`.

## 1. Provisionamento da instância

1. Acesse o console do Amazon Lightsail e clique em **Create instance**.
2. Escolha a região mais próxima dos usuários alvo e selecione a imagem **Linux/Unix → Ubuntu 22.04 LTS**.
3. Defina um plano de recursos compatível com a carga esperada (mínimo recomendado: 2 vCPUs, 4 GB RAM).
4. Gere ou selecione uma chave SSH para acesso administrativo.
5. Nomeie a instância (ex.: `sisacao-backend-prod`) e conclua a criação.

## 2. Configuração de rede e firewall

1. No painel da instância, abra a aba **Networking**.
2. Garanta que as portas a seguir estejam liberadas no firewall do Lightsail:
   - `22/tcp` para acesso SSH administrativo.
   - `80/tcp` e `443/tcp` para tráfego HTTP/HTTPS.
   - `8080/tcp` apenas se o balanceador/application load balancer externo acessar diretamente o Spring Boot.
3. Opcional: anexe um endereço IP estático para evitar mudança de endpoint após reinicializações.

## 3. Preparação do sistema operacional

Conecte-se à instância via SSH com a chave configurada no Lightsail:

```bash
ssh -i /caminho/para/sua-chave.pem ubuntu@IP_DA_INSTANCIA
```

Após o login, execute os comandos abaixo em sequência para preparar o ambiente.

```bash
# Atualizar lista de pacotes e aplicar correções
sudo apt update && sudo apt upgrade -y

# Instalar utilitários básicos usados ao longo do guia
sudo apt install -y unzip git ufw curl

# Instalar o Java 21 (necessário para o projeto Spring Boot)
sudo apt install -y openjdk-21-jdk

# (Opcional) Instalar Maven globalmente caso deseje compilar sem o wrapper
sudo apt install -y maven

# Verificar se o Java foi instalado corretamente
java -version

# (Opcional) validar instalação do Maven
mvn -v
```

Configure o firewall UFW permitindo apenas o tráfego essencial. Esses comandos garantem o acesso SSH e HTTP/HTTPS, além da porta 8080 caso seja usada para debug ou balanceador interno:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8080/tcp
sudo ufw enable
sudo ufw status
```

## 4. Criação de usuário de aplicação

1. Crie um usuário dedicado para executar o serviço, evitando rodar como `root`:

   ```bash
   sudo adduser --system --group --home /opt/sisacao sisacao
   sudo passwd -l sisacao  # impede login direto
   ```

2. Habilite permissões para publicar artefatos no diretório do usuário:

   ```bash
   sudo mkdir -p /opt/sisacao/app
   sudo chown -R sisacao:sisacao /opt/sisacao
   sudo chmod 750 /opt/sisacao /opt/sisacao/app
   ```

## 5. Obtenção do código fonte

Clone este repositório para a instância (ou faça deploy do artefato gerado pelo pipeline CI/CD):

```bash
sudo -u sisacao -H bash -c '
  cd /opt/sisacao
  git clone https://github.com/<sua-organizacao>/sisacao-8.git repo
'

# Se preferir usar chave SSH, configure previamente em ~/.ssh do usuário sisacao
sudo -u sisacao -H bash -c '
  mkdir -p ~/.ssh
  chmod 700 ~/.ssh
  # copie o arquivo id_rsa e configure as permissões adequadas
'
```

Atualize o repositório com as credenciais adequadas (HTTPS com token ou SSH) conforme a política da equipe.

## 6. Configuração de variáveis de ambiente

Crie um arquivo `/opt/sisacao/app/.env` (ou utilize o gerenciador de segredos escolhido) com as variáveis necessárias para acesso ao BigQuery e demais integrações. Use `cat` ou `tee` para gerar o arquivo diretamente pelo SSH:

```bash
sudo -u sisacao tee /opt/sisacao/app/.env > /dev/null <<'EOF'
GCP_PROJECT=ingestaokraken
BQ_TABLE=ingestaokraken.cotacao_intraday.cotacao_fechamento_diario
GCP_REGION=us-central1
SPRING_PROFILES_ACTIVE=prod
EOF
sudo chmod 600 /opt/sisacao/app/.env
```

Garanta que o arquivo seja acessível apenas pelo usuário da aplicação (`chmod 600`).

## 7. Build e empacotamento

Compile o projeto com o wrapper Maven distribuído no repositório:

```bash
cd /opt/sisacao/repo/backend/sisacao-backend
sudo -u sisacao ./mvnw clean package -DskipTests
sudo -u sisacao cp target/sisacao-backend-0.0.1-SNAPSHOT.jar /opt/sisacao/app/sisacao-backend.jar
sudo -u sisacao ls -lh /opt/sisacao/app/
```

O artefato pronto para produção ficará em `/opt/sisacao/app/sisacao-backend.jar`.

## 8. Configuração do serviço systemd

Crie o arquivo `/etc/systemd/system/sisacao-backend.service` com o seguinte conteúdo (substitua `JAVA_OPTS` caso deseje parâmetros adicionais):

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

Use o comando abaixo para criar o arquivo via SSH:

```bash
sudo tee /etc/systemd/system/sisacao-backend.service > /dev/null <<'EOF'
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
EOF
```

Recarregue o systemd e habilite o serviço:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sisacao-backend.service
sudo systemctl status sisacao-backend.service --no-pager
```

## 9. Configuração HTTPS (opcional, recomendada)

1. Anexe um certificado TLS à instância utilizando o **Lightsail Load Balancer** ou `certbot` (Let's Encrypt) diretamente na VM.
2. Caso utilize `certbot`, configure um `nginx` reverse proxy escutando na porta 443 e redirecionando tráfego para `http://127.0.0.1:8080`.
3. Atualize as regras do firewall para aceitar apenas tráfego HTTPS externo.

## 10. Observabilidade e logs

- Utilize `journalctl -u sisacao-backend -f` para acompanhar logs em tempo real.
- Valide se a aplicação está respondendo:

  ```bash
  curl -I http://127.0.0.1:8080/actuator/health
  ```
- Configure alarmes no CloudWatch/Lightsail para monitorar CPU, memória e reinícios do serviço.
- Considere integrar o Actuator com ferramentas de monitoramento (Prometheus/Grafana) expondo métricas em `/actuator/prometheus`.

## 11. Estratégia de atualização

1. Para publicar novas versões, execute `git pull` no diretório `/opt/sisacao/repo` ou distribua o JAR via pipeline:

   ```bash
   cd /opt/sisacao/repo
   sudo -u sisacao git pull origin main
   cd backend/sisacao-backend
   sudo -u sisacao ./mvnw clean package -DskipTests
   sudo -u sisacao cp target/sisacao-backend-0.0.1-SNAPSHOT.jar /opt/sisacao/app/sisacao-backend.jar
   ```

2. Reinicie o serviço após cada atualização:

   ```bash
   sudo systemctl restart sisacao-backend.service
   sudo systemctl status sisacao-backend.service --no-pager
   ```

3. Utilize implantações azuis/verdes ou instâncias secundárias para evitar indisponibilidade prolongada.

---

Seguindo este manual, o backend Spring Boot ficará pronto para atender requisições a partir do Amazon Lightsail com práticas básicas de segurança e operação.
