# Plano de implementação — Coleta de notícias para antecipação de eventos (queda pós-balanço)

## 1) Objetivo
Construir um pipeline de **detecção antecipada e triagem** de eventos em ações (ex.: quedas relevantes pós-balanço), combinando:

1. sinais de mercado (preço/volume),
2. sinais de calendário corporativo,
3. processamento de notícias em tempo quase real.

> Escopo: sistema de monitoramento e priorização para análise humana. Não constitui recomendação de investimento.

---

## 2) Hipóteses de antecipação
A antecipação será tratada em três janelas:

### 2.1 Pré-evento (T-5 dias até T-1 hora)
- Crescimento de volume acima da média (ex.: > 1.8x de 20 pregões)
- Aumento de frequência de notícias sobre a empresa/setor
- Mudança de tom em manchetes (mais termos de risco: guidance fraco, pressão de margem, alavancagem)
- Proximidade de calendário (resultado, teleconferência, fato relevante)

### 2.2 Janela de evento (T0)
- Publicação de notícia de resultado/fato relevante
- Classificação automática da notícia (miss/beat, margem, dívida, guidance)
- Confirmação de reação inicial de preço/volume

### 2.3 Pós-evento (T+1h a T+24h)
- Consolidação de notícias relacionadas
- Atualização de score de oportunidade/risco
- Encaminhamento para fila de análise com resumo automático

---

## 3) Arquitetura do pipeline

1. **Ingestão market data** (intraday + EOD)
2. **Ingestão de notícias** (RSS/API/scraping permitido)
3. **Enriquecimento NLP** (ticker, tema, sentimento, entidades)
4. **Correlator evento↔notícia** (janela temporal + relevância)
5. **Motor de score e priorização**
6. **Persistência + API + painel de backoffice**

---

## 4) Fontes de dados e política de coleta

### 4.1 Fontes de notícias
- Prioridade 1: APIs oficiais/licenciadas
- Prioridade 2: RSS públicos
- Prioridade 3: scraping leve, respeitando robots.txt e ToS

### 4.2 Campos mínimos por notícia
- `source`
- `url`
- `title`
- `published_at`
- `snippet/body_text` (conforme licença)
- `language`
- `tickers_detected`
- `content_hash`

### 4.3 Compliance
- Armazenar apenas conteúdo permitido por licença
- Preferir snippet + metadados quando texto integral não for permitido
- Registrar trilha de auditoria da origem de cada item

---

## 5) Estratégia de NLP (MVP → evolução)

### 5.1 MVP (regras + dicionários)
- Regex para tickers brasileiros (ex.: `\b[A-Z]{4}(3|4|11)\b`)
- Dicionário empresa→ticker (ex.: Yduqs→YDUQ3, Cogna→COGN3)
- Classificação por palavras-chave:
  - Balanço: resultado, 1T/2T/3T/4T, EBITDA, lucro
  - Guidance: projeção, revisão, outlook
  - Capital: dívida, alavancagem, covenant
  - Rentabilidade: margem, provisão, inadimplência

### 5.2 Evolução (ML/LLM)
- Modelo supervisionado por tema/causa provável
- Detecção de tom financeiro (sentimento específico de mercado)
- Extração estruturada: consenso vs realizado (quando disponível)

---

## 6) Motor de detecção e score

## 6.1 Gatilho base de evento
Gerar evento quando:
- `pct_change_intraday <= -X%` (ex.: -8%, -10%, -12%)
- OU gap negativo de abertura >= X%
- E volume relativo >= Y (ex.: 2x média)

## 6.2 Confirmadores por notícia
- notícia em janela de ±24h com tema de resultado/fato relevante
- ticker presente em título ou corpo

## 6.3 Score sugerido (0–100)
- Queda percentual: 0–35
- Volume anormal: 0–20
- Força da evidência textual: 0–25
- Recência da notícia: 0–10
- Penalidade de baixa liquidez/ruído: -10

### 6.4 Deduplicação
- Chave de evento: `ticker + data + tipo_evento`
- Chave de notícia: `content_hash`
- Agrupar múltiplas notícias no mesmo evento

---

## 7) Modelo de dados sugerido

### 7.1 Tabelas
- `market_event`
- `news_article`
- `event_news_link`
- `opportunity`
- `opportunity_audit_log`

### 7.2 Índices
- (`ticker`, `event_time`)
- `content_hash`
- (`status`, `score`, `created_at`)

---

## 8) Módulo de alertas e workflow

### 8.1 Canais
- Slack/Email/Webhook interno

### 8.2 Conteúdo do alerta
- Ticker, variação, volume relativo
- Top 2 causas prováveis
- Links das 3 notícias mais relevantes
- Resumo automático de 3–5 linhas

### 8.3 Estados operacionais
- `novo` → `em_analise` → `acompanhado` ou `descartado`

---

## 9) Métricas de qualidade (KPIs)
- Tempo entre notícia e alerta gerado (latência)
- % de eventos com notícia correlata
- Taxa de duplicidade
- Precisão de classificação temática (amostragem manual)
- Taxa de “alerta útil” reportada por analistas

---

## 10) Roadmap incremental

### Fase 1 (1–2 semanas): PoC
- 3 fontes de notícia
- 10 tickers líquidos
- regras heurísticas + score básico
- painel simples de listagem

### Fase 2 (2–4 semanas): Operacional
- mais fontes
- deduplicação robusta
- alertas em tempo real
- logs estruturados e métricas

### Fase 3 (4–8 semanas): Inteligência
- classificador supervisionado
- calibração por setor
- backtest histórico e ajuste de thresholds

---

## 11) Riscos e mitigação
- **Ruído/falso positivo:** ajustar pesos e filtros por setor
- **Limitação legal de conteúdo:** armazenar só metadados/snippets permitidos
- **Latência de fontes:** priorizar APIs e feeds com menor atraso
- **Quebra de scraping:** monitorar conectores e fallback por fonte

---

## 12) Próximos passos práticos no repositório
1. Criar pasta/módulo de domínio `opportunities` (modelos + regras + serviços)
2. Definir contratos de provider (`MarketDataProvider`, `NewsProvider`)
3. Implementar PoC de correlação evento↔notícia para YDUQ3 e COGN3
4. Expor endpoint de consulta das oportunidades priorizadas
5. Instrumentar logs e métricas desde a primeira versão
