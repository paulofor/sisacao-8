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