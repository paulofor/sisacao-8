# sisacao-8 — Especificação da Sprint 7 (Revisada)  
## Frontend (React/MUI) — Painel completo de Operação + Sinais (usando **seu** Backend)

**Projeto:** sisacao-8 (B3)  
**Sprint:** 7 (revisada para o stack atual)  
**Objetivo macro:** colocar no **seu frontend atual (`frontend/app`)** uma experiência completa para acompanhar:

- **Operação do pipeline** (health + silêncio)
- **DQ checks**
- **Incidentes**
- **Sinais do próximo pregão** (top 5) + histórico

> Dependência direta: Sprint 6 (endpoints `/ops/*` no backend).

---

## 1) UX alvo (sem criar outro app)

O frontend hoje é uma página única (“Monitoramento de Coletas”).  
Nesta sprint, evoluir para **um painel com navegação simples**.

### Opção recomendada (mínimo impacto)
- Criar um **menu por Tabs** no `AppBar` com 3–5 abas:
  1) **Coletas** (tela atual, sem remover nada)
  2) **Operação** (overview + pipeline + dq)
  3) **Sinais** (próximo pregão + histórico)
  4) **Incidentes** (abertos / últimos)
  5) (Opcional) **Logs** (backend logs)

> Sem react-router inicialmente (pode virar melhoria futura).

---

## 2) Entregáveis

### 2.1 Frontend (código)
- `src/api/ops.ts` (axios + types)
- `src/hooks/useOpsOverview.ts`
- `src/hooks/useOpsPipeline.ts`
- `src/hooks/useOpsDqLatest.ts`
- `src/hooks/useOpsSignalsNext.ts`
- `src/hooks/useOpsSignalsHistory.ts`
- `src/hooks/useOpsIncidentsOpen.ts`

Novos componentes (sugestão de estrutura):
- `src/components/ops/OpsOverviewCards.tsx`
- `src/components/ops/PipelineStatusTable.tsx`
- `src/components/ops/DqChecksTable.tsx`
- `src/components/ops/SignalsNextTable.tsx`
- `src/components/ops/SignalsHistoryTable.tsx`
- `src/components/ops/IncidentsTable.tsx`

### 2.2 UI/UX
- Aba “Operação”: visão geral + tabelas (pipeline e dq)
- Aba “Sinais”: top 5 + filtros (ticker/side) + histórico por data
- Aba “Incidentes”: lista com severidade e link/IDs
- Botão “Atualizar” deve atualizar a aba ativa (e opcionalmente todas).

---

## 3) Integração com o backend

### 3.1 Base URL
Você já tem:
- DEV: `http://localhost:8080`
- PROD: `/api`

Manter isso e apenas adicionar chamadas:
- `/ops/overview`
- `/ops/pipeline`
- `/ops/dq/latest`
- `/ops/signals/next`
- `/ops/signals/history`
- `/ops/incidents/open`

### 3.2 Tipos e normalização
Reaproveitar o estilo do `dataCollections.ts`:
- normalize datas (dayjs)
- normalize números (entry/target/stop)
- sempre retornar arrays (mesmo vazio) para a UI não quebrar

---

## 4) TanStack Query (padrão do projeto)

### 4.1 Regras de atualização (refetchInterval)
Sugestões práticas:
- `overview` e `pipeline`: `refetchInterval = 60_000` (1 min)
- `dq/latest`: `refetchInterval = 120_000` (2 min)
- `signals/next`: `refetchInterval = 300_000` (5 min) (ou sem intervalo e só refetch manual)
- `incidents/open`: `refetchInterval = 120_000` (2 min)
- `signals/history`: sem intervalo (carrega por demanda)

> TanStack Query suporta `staleTime` + `refetchInterval` diretamente no `useQuery`.

---

## 5) Componentes e layout (MUI)

### 5.1 Reusar padrão atual
Você já usa:
- `Container`, `Stack`, `Paper`, `Table`, `Alert`, `LinearProgress`

Manter o mesmo padrão para consistência.

### 5.2 “Semáforo”
Criar um componente `StatusChip` (OK/WARN/FAIL) usando `Chip` com cores:
- OK → success
- WARN → warning
- FAIL/ERROR → error

### 5.3 Tabelas recomendadas
- Pipeline: `Table` com colunas:
  - job, last run, status, silêncio, minutos desde, deadline, run_id
- DQ: `Table` com colunas:
  - check_name, status, created_at, detalhes (tooltip)
- Sinais (próximo pregão): `Table` com colunas:
  - ticker, side, entry, target, stop, score, rank, valid_for
  - (Opcional) botão “copiar ordem” (ex.: “COMPRA PETR4 se chegar a 43,00”)
- Histórico: com filtros por data (from/to) e limit

---

## 6) Plano de trabalho (tarefas)

### 6.1 Frontend — API e hooks
- [ ] Implementar `src/api/ops.ts` (types + fetch functions)
- [ ] Criar hooks `useOps*` com `useQuery`
- [ ] Adicionar “refetch on focus” e intervals conforme seção 4

### 6.2 Frontend — UI
- [ ] Refatorar `App.tsx` para suportar Tabs
- [ ] Criar componentes de Operação (cards + tabelas)
- [ ] Criar tela de Sinais (next + history)
- [ ] Criar tela de Incidentes
- [ ] Ajustar botão “Atualizar” para atualizar o contexto (aba ativa)

### 6.3 QA (Frontend)
- [ ] Simular API offline → mostrar `Alert` amigável
- [ ] Simular arrays vazios → UI sem quebrar (“sem dados”)
- [ ] Validar que auto-refresh não vira “spinner infinito”

### 6.4 Documentação
- [ ] `frontend/app/README.md` com:
  - como rodar local (backend + frontend)
  - variáveis: `VITE_API_BASE_URL`
  - como debugar chamadas

---

## 7) Critérios de aceite (Definition of Done)

Sprint 7 está pronta quando:
1) O frontend tem abas (ou navegação equivalente) e mantém a tela de Coletas funcionando.
2) A aba Operação mostra:
   - overview + pipeline status + dq latest
3) A aba Sinais mostra:
   - **top 5 do próximo pregão** com entry/target/stop
   - histórico por período (from/to)
4) A aba Incidentes mostra abertos/últimos.
5) Auto-refresh funciona e não degrada a UX.

---

## 8) Fora de escopo (Sprint 7)
- Login/SSO de usuário final (IAP/Firebase Auth)
- DataGrid MUI X (pode ser sprint futura; aqui usar `Table`)
- Features “modo trader” (marcar ordem enviada/executada)

---

## 9) Referências
```text
TanStack Query — useQuery (staleTime/refetchInterval):
https://tanstack.com/query/v2/docs/react/reference/useQuery

Spring Boot — Externalized config (para baseURL e envs do backend):
https://docs.spring.io/spring-boot/reference/features/external-config.html
```
