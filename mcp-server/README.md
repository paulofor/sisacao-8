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
