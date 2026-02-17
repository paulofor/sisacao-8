Perfeito. Vou gerar abaixo o conteúdo completo já estruturado em **Markdown**, pronto para você salvar como:

```
PLANO_EVOLUCAO_SISACAO8.md
```

---

# 📈 sisacao-8 — Plano de Evolução Técnica

## 🎯 Objetivo do Projeto

Desenvolver um sistema de geração de sinais para **swing trade sistemático na B3**, com:

* Geração de sinais no fechamento (até 22h)
* Entrada condicional no dia seguinte
* Alvo entre **6% e 8%**
* Stop loss entre **6% e 8%**
* Execução manual via ordens limitadas
* Máximo de 5 ativos simultâneos
* Uso inicial apenas de:

  * Intraday 15min (Google Finance)
  * Diário (arquivo oficial da B3)
  * API OpenAI (opcional em fases futuras)

---

# 🧠 Estratégia Base (Tese Inicial)

## Hipótese Principal

1. Se um ativo no dia seguinte ficar **abaixo de X**, há alta probabilidade de subir Y%.
2. Se um ativo no dia seguinte ficar **acima de X**, há alta probabilidade de cair Y%.

Modelo caracterizado como:

> Estratégia de reversão à média com alvo e stop fixos.

---

## 📌 Estrutura do Trade

Exemplo:

* Compra condicional PETR4 a R$ 43,00
* Target: +7%
* Stop: -7%
* Validade: pregão seguinte

---

# 🏗 Arquitetura do Sistema

## Módulos Principais

### 1️⃣ Coleta e Padronização de Dados

Fontes:

* Intraday 15min → Google Finance
* Diário → Arquivo oficial da B3

Modelo padrão de candle:

```python
class Candle:
    date
    open
    high
    low
    close
    volume
```

Separação lógica:

* tabela_diaria
* tabela_intraday_15m

---

### 2️⃣ Motor de Geração de Sinais (EOD)

Executado diariamente até 22h.

Processo:

1. Ler dados diários
2. Calcular nível X
3. Gerar sinal condicional
4. Definir target e stop
5. Exportar JSON ou CSV

Exemplo de saída:

```json
{
  "ativo": "PETR4",
  "tipo": "COMPRA_CONDICIONAL",
  "entrada": 43.00,
  "target": 46.01,
  "stop": 40.00,
  "validade": "2026-02-17"
}
```

---

### 3️⃣ Motor de Backtesting (Baseado em OHLC Diário)

⚠ Não usar intraday para validar execução.

Simulação:

Para cada dia histórico:

1. Gerar sinal no dia D
2. No dia D+1:

   * Se low <= entrada (compra) → executa
   * Se high >= entrada (venda) → executa
3. Após entrada:

   * Se high >= target → lucro
   * Se low <= stop → prejuízo

---

### 4️⃣ Gestão de Risco e Portfólio

Regras:

* Máximo 5 ativos simultâneos
* Se houver mais de 5 sinais:

  * Selecionar os 5 melhores via ranking

Possível score:

```
score = probabilidade_historica * volatilidade
```

---

### 5️⃣ Camada de IA (Fase Avançada)

Somente após validação estatística.

Possíveis aplicações:

* Classificação de regime de mercado
* Classificação de qualidade do sinal
* Análise de sentimento de notícias (Reuters, CVM, RI)

---

# 📊 Backtesting — Métricas Obrigatórias

O sistema deve calcular:

* Taxa de acerto
* Payoff médio
* Expectativa matemática
* Máximo drawdown
* Duração média do trade
* Número médio de posições simultâneas

Expectativa matemática:

```
Expectativa = (taxa_acerto * ganho_medio) - (taxa_erro * perda_media)
```

Se negativa → estratégia inválida.

---

# 🧪 Definição Inicial de X e Y

## Versão Inicial Simples

* X_compra = fechamento - 2%
* X_venda = fechamento + 2%
* Y (target) = 7%
* Stop = 7%

Depois testar variações:

* Baseado em mínima/máxima anterior
* Baseado em volatilidade (ATR)
* Baseado em desvio padrão

---

# 📅 Planejamento por Sprint

---

## 🟢 Sprint 1 — Estrutura e Dados

Objetivo: Base sólida.

* Padronizar estrutura Candle
* Organizar banco diário
* Criar agregação opcional 15m → 1h
* Implementar geração básica de X
* Exportar sinais EOD

---

## 🟢 Sprint 2 — Backtest da Tese

Objetivo: Validar estatística.

* Simular 3–5 anos de histórico
* Implementar lógica OHLC
* Calcular métricas
* Avaliar expectativa matemática

---

## 🟢 Sprint 3 — Portfólio e Limite de 5 Ativos

Objetivo: Simular realidade operacional.

* Implementar controle de posições abertas
* Criar ranking de sinais
* Simular capital fixo
* Medir drawdown real

---

## 🟢 Sprint 4 — Otimização

Objetivo: Melhorar robustez.

* Testar múltiplos valores de X
* Testar múltiplos valores de Y
* Testar volatilidade adaptativa
* Separar mercado por regimes

---

## 🟢 Sprint 5 — IA Aplicada

Somente após estratégia ser positiva.

* IA para classificar regime de mercado
* IA para classificar qualidade do sinal
* Análise de sentimento via OpenAI
* Filtro de notícias relevantes

---

# 📰 Sobre Notícias (Reuters)

Reuters é uma excelente fonte:

* Alta credibilidade
* Cobertura macroeconômica e corporativa
* Notícias públicas

Mas:

* Pode haver bloqueio de scraping
* Alternativas:

  * CVM (fatos relevantes)
  * B3 comunicados
  * Relações com Investidores
  * Banco Central

⚠ Recomendação:
Validar estratégia estatística antes de usar notícias.

---

# ⚠ Considerações Realistas

* Meta de 6–8% é alta para swing trade.
* Taxa de acerto pode ficar entre 40–55%.
* Estratégia tende a funcionar melhor:

  * Em mercados laterais
  * Em alta volatilidade
* Pode falhar em tendências fortes.

Por isso, regime de mercado será importante no futuro.

---

# 📌 Prioridade Estratégica

Antes de usar IA:

1. Validar matemática.
2. Validar expectativa.
3. Medir drawdown.
4. Testar robustez.

90% dos sistemas falham na fase de backtest.

---

# 🚀 Conclusão

O projeto sisacao-8 é tecnicamente viável.

Estratégia:

* Começar simples
* Validar estatística
* Controlar risco
* Evoluir para IA apenas após base sólida

---

**Próximo passo recomendado:**
Implementar o motor de backtest diário e validar 3 anos de histórico.

---

Se você quiser, posso agora:

* Gerar versão formatada como README com badge e estrutura GitHub
* Gerar versão com checklist técnico por tarefa
* Criar diagrama de arquitetura do sistema
* Criar estrutura inicial de pastas do projeto

Qual você prefere evoluir agora?
