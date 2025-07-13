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
├── functions/                # **Vazio por enquanto. NÃO adicionar código agora.**
│   └── README.md             # Mantém instruções genéricas para criar funções futuramente
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
- **Estado atual:** Estrutura de projeto configurada; **nenhuma Cloud Function foi implementada ainda**.
- **Próximo marco:** Definir a primeira função (nome, assinatura, dependências) antes de qualquer implementação.

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
- `BQ_TABLE` → `project.dataset.tabela`
- `GCP_PROJECT` → ID do projeto GCP

---
> **Importante:** Não criar ou referenciar funções neste momento. Atualize este guia à medida que novos componentes sejam adicionados.
```

---

## Próximos passos sugeridos

1. **Secrets**: Configure no GitHub os segredos `GCP_SA_KEY`, `GCP_PROJECT`, `BQ_TABLE`.
2. **Pre‑commit hooks**: Ative `black`, `flake8`, `isort` e `pre‑commit`.
3. **Revisar AGENTS.md**: Após definição da primeira função, adicione detalhes no guia.
4. **Planejamento**: Reunir requisitos e design da primeira Cloud Function antes de escrever qualquer código.

---

> As funções serão adicionadas somente após a etapa de planejamento. Por enquanto, concentre‑se em configurar ambiente, CI e documentação.
