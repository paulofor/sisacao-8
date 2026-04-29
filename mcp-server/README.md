# MCP Server (sisacao-8)

Estrutura inicial para um **MCP Server** dedicado a consultas operacionais do projeto:

1. Leitura de tabelas no **BigQuery**.
2. Consulta de **logs das Cloud Functions** no Cloud Logging.

## Objetivo desta etapa

Esta pasta agora publica um MCP Server ativo para clientes remotos, com transporte
`streamable-http` e endpoint em `/mcp`.

## Estrutura

```text
mcp-server/
├── README.md
├── requirements.txt
├── .env.example
└── src/
    └── server.py
```

## Endereço padrão do servidor (VPS)

- Host: `187.45.254.75`
- Porta publicada no host: `8080`
- Endpoint MCP: `http://187.45.254.75:8080/mcp`

## Próximos incrementos sugeridos

- Implementar autenticação com Service Account (ADC ou arquivo JSON).
- Expor ferramentas MCP para:
  - listar datasets/tabelas do BigQuery;
  - executar queries parametrizadas com limites de segurança;
  - consultar logs de funções por janela de tempo e severidade.
- Adicionar testes de integração com mocks de BigQuery e Logging.
- Publicar container para execução local e em ambiente de homologação.

## Execução local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r mcp-server/requirements.txt
python mcp-server/src/server.py
```

Variáveis opcionais:

- `MCP_HOST` (padrão `0.0.0.0`)
- `MCP_PORT` (padrão `8080`)
- `MCP_TRANSPORT` (padrão `streamable-http`)
- `GCP_PROJECT` e `GCP_REGION`

Credenciais do GCP (mesmo padrão do backend):

- `GCP_SERVICE_ACCOUNT_JSON` (JSON bruto)
- `GCP_SERVICE_ACCOUNT_JSON_BASE64` (JSON em Base64)
- `GOOGLE_APPLICATION_CREDENTIALS` (caminho do arquivo JSON)

Prioridade de leitura das credenciais: JSON bruto -> Base64 -> arquivo -> ADC padrão do ambiente.

Ferramentas MCP disponíveis nesta etapa:

- `ping`
- `runtime_config`
- `bigquery_access_check` (executa `SELECT 1 AS ok`)

## Deploy automatizado para VPS (GitHub Actions)

Workflow: `.github/workflows/deploy-mcp-vps.yml`

- Builda e publica a imagem Docker do MCP Server no `ghcr.io`.
- Conecta via SSH no host `187.45.254.75`.
- Atualiza o container `sisacao8-mcp-server` com `docker pull` + `docker run`,
  publicando a porta `8080:8080`.

Secrets necessários no repositório:

- `VPS_SSH_USER`
- `VPS_SSH_PRIVATE_KEY`
- `GHCR_USERNAME`
- `GHCR_TOKEN` (com permissão de leitura de pacotes)
- `GCP_PROJECT`
- `GCP_REGION`
