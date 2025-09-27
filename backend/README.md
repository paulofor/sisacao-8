# Backend

Este diretório abrigará o serviço Java (Spring Boot ou Quarkus) responsável por expor APIs REST e integrações com o BigQuery para leitura de sinais, parâmetros e controle de treinamentos de modelos.

Principais componentes esperados:
- Camada de domínio para sinais, execuções de treinamento e parametrizações.
- Serviços e repositórios que encapsulam consultas ao BigQuery e orquestram jobs externos de ML.
- Endpoints REST/WebSocket protegidos por OAuth2/OpenID.

Mantenha a estrutura de código organizada em módulos coerentes (ex.: `api/`, `service/`, `repository/`) e configure testes automatizados desde o início.
