# Plano de implementação — Pesquisa de oportunidades (ex.: YDUQ3 - queda ~14% pós-balanço)

## 1) Contexto e motivação
Notícias recentes apontam forte queda de ações como **YDUQ3** (Yduqs) e **COGN3** (Cogna) após divulgação de resultados, com o mercado reagindo a componentes do balanço, guidance/expectativas e leitura de qualidade de lucro.

Fontes (para rastreabilidade):
- InfoMoney — “Yduqs (YDUQ3) e Cogna (COGN3) despencam após balanços: o que aconteceu?”
  - https://www.infomoney.com.br/mercados/yduqs-yduq3-e-cogna-cogn3-despencam-apos-balancos-o-que-aconteceu/
- E-Investidor/Estadão — “Yduqs (YDUQ3) e CSN (CSNA3) tombam… após balanço 4T25”
  - https://einvestidor.estadao.com.br/ultimas/yduqs-yduq3-csn-csna3-acoes-balanco-4t25/
- Finance News — “Yduqs (YDUQ3) tem lucro ajustado de R$ 60,2 milhões no 4T25”
  - https://financenews.com.br/2026/03/yduqs-yduq3-tem-lucro-ajustado-de-r-602-milhoes-no-4t25/

Objetivo do sistema: **detectar automaticamente eventos de queda relevante “pós-notícia/pós-balanço”**, coletar contexto (headline, resumo, motivo provável), e **priorizar oportunidades** para análise (ex.: “queda 14% intraday em YDUQ3 após balanço”).

> Observação importante: este plano descreve uma implementação de *pesquisa e triagem* de oportunidades e não constitui recomendação de investimento.

---

## 2) Definição do que é “oportunidade” (hipóteses de sinal)
Criar regras configuráveis (por ativo/segmento) para gerar *alerts* e itens de pesquisa.

### 2.1. Evento de preço (gatilhos)
- **Queda intraday** ≥ X% (ex.: 8%, 10%, 12%, 14%).
- **Gap de abertura** negativo ≥ X%.
- **Queda acumulada em N dias** ≥ X%.
- **Volume** ≥ Y vezes a média (ex.: 2x/3x média de 20 pregões).

### 2.2. Evento de calendário/notícia (confirmadores)
- Proximidade de:
  - divulgação de resultados (trimestral/anual),
  - teleconferência,
  - fato relevante,
  - rebaixamento/alteração de rating,
  - guidance/revisão de projeções.
- Presença de notícia que mencione: “após balanço”, “4T25”, “resultado”, “lucro ajustado”, “Ebitda”, “endividamento”, “capex”, “inadimplência”, “ticket”, “margem”, “provisões”, etc.

### 2.3. Qualidade do evento (classificação)
Classificar o motivo provável da queda:
- **Expectativa vs realizado** (miss/beat).
- **Margem/eficiência**.
- **Endividamento/estrutura de capital**.
- **Guidance e perspectiva**.
- **Fatores não recorrentes**.

---

## 3) Arquitetura proposta (alto nível)
Pipeline em 5 etapas:

1. **Ingestão de dados de mercado** (preço/volume intraday e EOD)
2. **Detecção de eventos** (regras e thresholds)
3. **Enriquecimento com notícias** (busca, scraping permitido, RSS/licenças)
4. **NLP/extração** (ticker, causa provável, sentimento, entidades)
5. **Rank + fila de pesquisa** (priorização, deduplicação, workflow)

---

## 4) Componentes e entregáveis

### 4.1. Módulo de Market Data
**Objetivo:** ter candles e variações para detectar movimentos como “YDUQ3 caiu 14%”.

- Interface sugerida:
  - `MarketDataProvider.get_quote(ticker, date_time_range)`
  - `MarketDataProvider.get_daily(ticker, start, end)`
- Campos mínimos:
  - preço atual, abertura, máxima, mínima, fechamento, volume
  - variação % intraday e vs fechamento anterior

**Atenção:** caso o sistema não tenha um provedor, selecionar um (B3/Corretora/serviço) e implementar adaptador.

### 4.2. Módulo de News Ingestion
**Objetivo:** coletar e indexar notícias e metadados relacionados ao evento.

- Estratégias:
  - RSS/feeds (quando disponíveis)
  - scraping leve (respeitando robots e termos)
  - integração com API (se existir/licenciada)

- Campos a armazenar:
  - `source`, `url`, `title`, `published_at`, `body_text` (ou snippet), `tickers_detected`
  - hash do conteúdo para deduplicação

### 4.3. Extração de tickers e temas (NLP)
**Objetivo:** ligar o evento de preço às notícias corretas.

- Regras heurísticas iniciais:
  - regex para tickers brasileiros: `\b[A-Z]{4}3\b` (e variantes 4/11 etc.)
  - dicionário de nomes: “Yduqs”→YDUQ3, “Cogna”→COGN3
- Enriquecimento:
  - classificar notícia como “resultado/balanço” quando encontrar termos (ex.: “4T25”, “lucro ajustado”, “Ebitda”, “resultado do trimestre”).

### 4.4. Motor de detecção e priorização
**Objetivo:** gerar um item de pesquisa quando há evento relevante + notícia correlata.

- Exemplo de score (0–100):
  - magnitude da queda (peso alto)
  - volume anormal (peso médio)
  - confirmação por notícia de balanço (peso alto)
  - “novidade” (primeira vez no dia) (peso médio)
  - risco (volatilidade, liquidez) (penalidade)

- Deduplicação:
  - por ticker+data (não gerar 20 alerts iguais)
  - agrupar múltiplas notícias no mesmo evento

### 4.5. UX/Workflow (backoffice)
**Objetivo:** permitir que analistas vejam e investiguem.

- Tela “Oportunidades”:
  - lista por score
  - variação %, volume, links das notícias
  - tags: {balanço, guidance, dívida, margem, etc.}
  - status: {novo, em análise, descartado, acompanhado}

- Ações:
  - adicionar nota
  - anexar relatório
  - criar watchlist/alerta de acompanhamento

---

## 5) Modelo de dados (sugestão)

### 5.1. Tabelas
- `market_event`
  - `id`, `ticker`, `event_type`, `event_time`, `pct_change`, `volume_ratio`, `raw_payload`
- `news_article`
  - `id`, `source`, `url`, `title`, `published_at`, `content_hash`, `body_text`
- `event_news_link`
  - `event_id`, `news_id`, `relevance_score`
- `opportunity`
  - `id`, `ticker`, `event_id`, `score`, `status`, `created_at`, `tags`, `summary`

### 5.2. Observações
- Garantir índice em (`ticker`, `event_time`) e em `content_hash`.
- Guardar `raw_payload` para auditoria.

---

## 6) Regras específicas para o caso “pós-balanço” (ex.: YDUQ3)

### 6.1. Heurística mínima
Gerar oportunidade quando:
- `pct_change_intraday <= -10%` **E**
- houver notícia em ±24h contendo `balanço|resultado|4T|trimestre|lucro|Ebitda|guidance` **E**
- ticker identificado no título ou no corpo.

### 6.2. Resumo automático (template)
- “{TICKER} caiu {X}% em {DATA} após divulgação de resultados. Notícias citam {TOP_2_TEMAS}. Link(s): …”

### 6.3. Checklist de pesquisa (para o analista)
- Comparar consenso vs realizado (receita, EBITDA, lucro)
- Itens não recorrentes
- Evolução de margem
- Dívida líquida/EBITDA e cronograma
- Comentários de guidance
- Reação de casas/relatórios

---

## 7) Observabilidade e qualidade
- Logs estruturados por etapa (ingestão, detecção, NLP, ranking)
- Métricas:
  - nº de eventos detectados/dia
  - % com notícia associada
  - tempo até criar oportunidade após movimento
  - taxa de duplicidade

---

## 8) Plano de execução (milestones)

### Milestone 1 — Base de eventos de mercado
- Implementar provider e armazenar candles/variações.
- Criar job scheduler (intervalo: 1–5 min durante pregão).

### Milestone 2 — Ingestão de notícias + indexação
- Conectores por fonte (inicialmente as 3 fontes acima como prova de conceito).
- Normalização e deduplicação por hash.

### Milestone 3 — Detecção e ligação evento↔notícia
- Implementar heurísticas de ticker e “pós-balanço”.
- Criar entidade `opportunity` e a fila.

### Milestone 4 — Ranking e UI
- Score, filtros e workflow.
- Links diretos e geração de resumo.

### Milestone 5 — Hardening
- Ajuste de thresholds por setor
- Backtests (quantos eventos relevantes foram capturados)
- Alertas (Slack/email)

---

## 9) Riscos e compliance
- Respeitar termos de uso das fontes e direitos autorais (armazenar snippets quando necessário).
- Garantir que o sistema deixe claro que é triagem/monitoramento, não recomendação.
- Cuidar com latência de dados e dados atrasados.

---

## 10) Próximos passos práticos no repositório
1. Mapear onde ficam jobs/schedulers e onde já existe ingestão de dados (market/news).
2. Criar módulo `opportunities` (detector + modelos + endpoints).
3. Implementar prova de conceito para:
   - `YDUQ3` e `COGN3` com gatilho de queda e correlação com notícias.
