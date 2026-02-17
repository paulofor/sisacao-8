# sisacao-8

Estrutura inicial do repositório para automação de coleta de cotações de ações e carga no **BigQuery** via **Google Cloud Functions** (as funções serão adicionadas em etapas futuras – **nenhuma função será criada agora**).

---

## Árvore de diretórios

```text
sisacao-8/
├── .github/
│   └── workflows/
│       ├── ci.yml            # Lint + testes automáticos
│       └── deploy.yml        # Deploy contínuo para o GCP (placeholder)
├── .gitignore                # Padrão Python + VSCode + Mac & Linux
├── AGENTS.md                 # Orienta o Codex sobre o projeto
├── README.md                 # Visão geral e instruções de uso
├── requirements.txt          # Dependências compartilhadas para dev local
├── config/
│   └── env.example           # Variáveis de ambiente de exemplo (BQ_TABLE, GCP_PROJECT…)
├── functions/
│   ├── README.md             # Instruções genéricas
│   └── get_stock_data/
│       ├── main.py           # Primeira Cloud Function
│       └── requirements.txt  # Dependências da função
├── scripts/
│   └── local_test.py         # Framework para testes locais (ficará ocioso até existirem funções)
└── tests/
    └── test_placeholder.py   # Placeholder inicial para testes
```

---

## Descrição dos principais arquivos e pastas

* **AGENTS.md**: Arquivo dedicado a fornecer contexto e diretrizes ao OpenAI Codex (ou outros agentes de IA) sobre o domínio do projeto, convenções de código, dependências externas e tarefas pendentes. **Não descreve nenhuma função ainda**.
* **.github/workflows/**: CI/CD – o *ci.yml* executa lint (`flake8`), formatação (`black`) e testes (`pytest`). O *deploy.yml* continua como placeholder, sem deploy de funções.
* **requirements.txt**: Lista de pacotes de desenvolvimento compartilhados.
* **functions/**: Diretório reservado; permanece vazio até que decidamos criar a primeira Cloud Function.

---

## Conteúdo sugerido para `AGENTS.md`

```markdown
# Codex Agents Guide – sisacao‑8

Este arquivo fornece contexto a agentes de IA (OpenAI Codex, ChatGPT, etc.) sobre este repositório.

## 1. Visão geral do projeto
- **Objetivo:** Coletar cotações de ações em tempo quase‑real e armazená‑las no BigQuery para análises posteriores.
- **Estado atual:** Primeira Cloud Function implementada (`get_stock_data`).
- **Próximo marco:** Evoluir o processo de coleta e documentar novas funções.

## 2. Convenções de código
- **Formatação:** `black` + `isort`
- **Lint:** `flake8` com `flake8-bugbear`
- **Typing:** `mypy`
- **Estrutura de futuras funções:** cada função residirá em `functions/<nome_da_funcao>/` com `main.py` e `requirements.txt` minimalista.

## 3. Dependências externas aprovadas (para uso futuro)
| Pacote | Uso | Observação |
|--------|-----|-----------|
| `yfinance` | Download de cotações | Substituível por AlphaVantage ou IEX se necessário. |
| `google-cloud-bigquery` | Inserção de dados | Versão `>=3.12`. |
| `functions-framework` | Testes locais | Dev only. |

## 4. Variáveis de ambiente essenciais (pré‑definidas)
- `BQ_TABLE` → `ingestaokraken.cotacao_intraday.candles_diarios`
- Tabela intraday utilizada pelas funções `google_finance_price` e monitoramentos derivados:
  `ingestaokraken.cotacao_intraday.cotacao_bovespa`
- `GCP_PROJECT` → `ingestaokraken`
- `GCP_REGION` → `us-central1`

---
> **Importante:** Novas funções devem seguir o padrão deste repositório. Mantenha o guia atualizado a cada adição.
```

---

## Próximos passos sugeridos

1. **Secrets**: Configure no GitHub os segredos `GCP_SA_KEY`, `GCP_PROJECT`, `BQ_TABLE`.
2. **Pre‑commit hooks**: Ative `black`, `flake8`, `isort` e `pre‑commit`.
3. **Revisar AGENTS.md**: Após definição da primeira função, adicione detalhes no guia.
4. **Planejamento**: Reunir requisitos e design da primeira Cloud Function antes de escrever qualquer código.

---

## Serviços em execução

- **Backend web** e **frontend web** estão publicados na VPS em execução no endereço: <http://34.194.252.70/>.

---

## Princípios de arquitetura da plataforma

1. **Backend Java + BigQuery**: Um serviço REST (Spring Boot ou Quarkus) fornecerá APIs para consultar sinais, parâmetros e execuções de treinamento diretamente das tabelas no BigQuery, aplicando camadas de serviço/repositório para encapsular o acesso aos dados.
2. **Frontend web moderno**: Uma aplicação single-page (React ou Vue) consumirá as APIs expostas pelo backend para construir dashboards ricos com controles de sinais, acompanhamento de jobs de treinamento e ajustes de parâmetros.
3. **Integração desacoplada**: Comunicação exclusiva via HTTP/JSON (ou WebSockets quando necessário), com autenticação unificada (OAuth2/OpenID) e versionamento de endpoints para facilitar evoluções independentes entre frontend e backend.
4. **Observabilidade e governança**: Logs estruturados, métricas e rastreamento distribuído devem ser configurados desde o início para acompanhar pipelines de dados, execuções de ML e interações dos usuários.
5. **Infraestrutura GCP**: O projeto reutiliza as variáveis `GCP_PROJECT`, `BQ_TABLE` e `GCP_REGION`, além de service accounts dedicadas para executar consultas e jobs de BigQuery com mínimo privilégio.

---

> As funções serão adicionadas somente após a etapa de planejamento. Por enquanto, concentre‑se em configurar ambiente, CI e documentação.
