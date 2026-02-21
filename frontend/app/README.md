# Painel Operacional — Sisacao-8

Interface web construída com React, Vite e Material UI para acompanhar as pipelines de ingestão (coletas BigQuery), operação
do pipeline (`/ops/*`), sinais do próximo pregão e incidentes em aberto — tudo em uma única aplicação.

## Principais recursos

- **Abas dedicadas** no AppBar:
  - **Coletas:** visão atual com filtros, busca, cards intraday e tabela de mensagens.
  - **Operação:** overview com "semáforo" + tabelas de pipeline e data-quality.
  - **Sinais:** top 5 do próximo pregão com filtros por ticker/side e histórico por data.
  - **Incidentes:** lista dos incidentes abertos com severidade e run IDs.
- Auto-refresh configurado via TanStack Query (intervalos de 1 a 5 minutos conforme endpoint) com atualização manual por aba.
- Tratamento de estados de erro/offline com `Alert` e mensagens "sem dados" para respostas vazias.

## Como rodar localmente

1. **Backend** (Spring Boot) — necessário para os endpoints `/data-collections/*` e `/ops/*`:
   ```bash
   cd backend
   ./mvnw spring-boot:run
   ```
   O serviço ficará disponível em `http://localhost:8080`.

2. **Frontend**:
   ```bash
   cd frontend/app
   cp .env.example .env.local   # ajuste se precisar apontar para outra base URL
   npm install --include=dev
   npm run dev
   ```
   O Vite abrirá em `http://localhost:5173` (ou porta indicada no terminal).

3. Para gerar a build de produção: `npm run build` (gera artefatos em `dist/`).

## Variáveis de ambiente

- `VITE_API_BASE_URL` — base dos endpoints REST.
  - **Padrão (recomendado):** vazio (`""`), usando o backend no mesmo host do frontend (`/ops/*` e `/data-collections/*`).
  - **Ambiente local separado:** definir `VITE_API_BASE_URL=http://localhost:8080`.
  - **Produção com reverse-proxy em `/api`:** definir `VITE_API_BASE_URL=/api`.
- Quando `VITE_API_BASE_URL` não está definida, a aplicação usa base vazia (`""`) por padrão.

## Depurando chamadas HTTP

- Utilize o DevTools do navegador (aba **Network**) para verificar cada request feito por aba.
- Todas as chamadas passam por `src/api/client.ts` (Axios). Ajustar `VITE_API_BASE_URL` e recarregar a página é suficiente para
  testar contra ambientes diferentes.
- Em caso de erro, as abas exibem alertas com instruções para verificar o backend — útil para simular API offline.

## Estrutura relevante

```
src/
├── api/                         # Clientes HTTP e contratos de dados (data-collections + ops)
├── components/
│   ├── ops/                     # Tabelas e cards da aba Operação/Sinais/Incidentes
│   └── tabs/                    # Containers principais de cada aba
├── hooks/                       # Hooks customizados usando TanStack Query
├── theme.ts                     # Tema do Material UI
├── App.tsx                      # Composição das abas, AppBar e botão de atualização
└── index.css                    # Estilos globais
```

## Endpoints consumidos

- `/data-collections/messages`
- `/data-collections/intraday-summary`
- `/data-collections/intraday-daily-counts`
- `/data-collections/intraday-latest-records`
- `/ops/overview`
- `/ops/pipeline`
- `/ops/dq/latest`
- `/ops/signals/next`
- `/ops/signals/history`
- `/ops/incidents/open`

Consulte [`docs/ops_api.md`](../../docs/ops_api.md) para o contrato completo dos endpoints operacionais.
