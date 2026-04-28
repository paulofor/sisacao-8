# MCP Server (sisacao-8)

Estrutura inicial para um **MCP Server** dedicado a consultas operacionais do projeto:

1. Leitura de tabelas no **BigQuery**.
2. Consulta de **logs das Cloud Functions** no Cloud Logging.

## Objetivo desta etapa

Esta pasta cria apenas o *bootstrap* do serviço para evoluirmos em próximas entregas.

## Estrutura

```text
mcp-server/
├── README.md
├── requirements.txt
├── .env.example
└── src/
    └── server.py
```

## Próximos incrementos sugeridos

- Implementar autenticação com Service Account (ADC ou arquivo JSON).
- Expor ferramentas MCP para:
  - listar datasets/tabelas do BigQuery;
  - executar queries parametrizadas com limites de segurança;
  - consultar logs de funções por janela de tempo e severidade.
- Adicionar testes de integração com mocks de BigQuery e Logging.
- Publicar container para execução local e em ambiente de homologação.

## Execução local (placeholder)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r mcp-server/requirements.txt
python mcp-server/src/server.py
```

## Deploy automatizado para VPS (GitHub Actions)

Workflow: `.github/workflows/deploy-mcp-vps.yml`

- Builda e publica a imagem Docker do MCP Server no `ghcr.io`.
- Conecta via SSH no host `187.45.254.75`.
- Atualiza o container `sisacao8-mcp-server` com `docker pull` + `docker run`.

Secrets necessários no repositório:

- `VPS_SSH_USER`
- `VPS_SSH_PRIVATE_KEY`
- `GHCR_USERNAME`
- `GHCR_TOKEN` (com permissão de leitura de pacotes)
- `GCP_PROJECT`
- `GCP_REGION`
