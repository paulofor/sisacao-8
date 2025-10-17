# Backend

Este diretório abrigará o serviço Java (Spring Boot) responsável por expor APIs REST e integrações com o BigQuery para a leitura de sinais, parâmetros e controle de treinamentos de modelos.

## Estrutura atual

- `sisacao-backend/`: projeto Spring Boot inicializado com Maven (Java 21, starters *web* e *actuator*).

## Como executar localmente

1. Entre no diretório do projeto: `cd backend/sisacao-backend`.
2. Execute testes e baixe dependências com o wrapper Maven: `./mvnw test`.
3. Suba a aplicação localmente: `./mvnw spring-boot:run`.

O endpoint padrão ficará disponível em `http://localhost:8080/`.

### Logs via Actuator

Com a aplicação em execução é possível baixar os logs recentes acessando `http://localhost:8080/actuator/logfile`. O arquivo exposto é o mesmo configurado em `logging.file.name` (por padrão `logs/sisacao-backend.log`). Defina a variável de ambiente `APP_LOG_FILE` para sobrescrever o caminho tanto do arquivo quanto do endpoint.

## Guia de preparação do ambiente

Para preparar a infraestrutura de produção (Amazon Lightsail), consulte o documento [docs/backend-lightsail-setup.md](../docs/backend-lightsail-setup.md), que detalha o provisionamento da instância, instalação de dependências e publicação do serviço Spring Boot.
