# Fase 7 — Preparação para operação controlada

## Objetivo executado

Esta etapa prepara a governança necessária para que uma estratégia quantitativa só avance para **piloto com capital real reduzido** quando tiver passado por checklist técnico, validação estatística, paper trading e limites de risco auditáveis.

A implementação não automatiza envio de ordens reais. Ela cria a camada de decisão, risco e monitoramento que deve existir antes de qualquer operação controlada.

## Artefato criado

- Script BigQuery: `infra/bq/14_quant_phase7_controlled_operation.sql`.

## Componentes técnicos

### `quant_controlled_operation_risk_config`

Tabela de configuração versionada dos limites de risco do piloto:

- capital máximo permitido;
- risco máximo por trade;
- limite de perda diária;
- limite de perda semanal;
- limite de exposição por estratégia;
- limite de exposição por ticker;
- limite de exposição por setor;
- máximo de posições abertas;
- política de pausa automática quando houver violação;
- requisitos mínimos de paper trading e robustez.

A versão inicial é `controlled_operation_risk_v1`/`v1`, com status `ativa`.

### `quant_strategy_approval_checklist`

Tabela de checklist auditável por estratégia e versão:

- amostra mínima;
- expectativa positiva;
- drawdown aceitável;
- validação fora da amostra;
- robustez estatística;
- paper trading consistente;
- limites de risco aprovados;
- decisão manual: aprovar, pausar, reprovar ou manter pendente.

### `quant_controlled_operation_risk_snapshots`

Tabela de snapshots de risco para alimentar a tela **Risco e Limites**:

- exposição atual por estratégia, ticker e setor;
- PnL diário e semanal;
- posições abertas;
- risco por trade;
- limite violado;
- nível de alerta;
- ação recomendada.

### `quant_strategy_committee_decisions`

Tabela de decisões do **Comitê de Estratégias**:

- aprovar piloto;
- pausar estratégia;
- reprovar estratégia;
- retomar estratégia;
- registrar responsável, justificativa e janela de vigência.

### `vw_quant_phase7_strategy_committee`

View consolidada para a tela **Comitê de Estratégias**. Ela cruza:

- métricas de backtest da Fase 1;
- robustez e validação fora da amostra da Fase 5;
- resultados de paper trading da Fase 6;
- checklist manual da Fase 7;
- configuração ativa de risco.

A view entrega status recomendado entre `pesquisa`, `validacao`, `paper_trading`, `piloto`, `reprovada` e `pausada`.

### `vw_quant_phase7_risk_limits`

View para a tela **Risco e Limites**:

- exposição atual;
- perda acumulada diária e semanal;
- limites configurados;
- status de risco;
- recomendação operacional.

### `vw_quant_phase7_shutdown_alerts`

View de alertas operacionais para desligamento ou redução de exposição quando houver:

- limite violado;
- proximidade do limite diário;
- proximidade do limite semanal;
- máximo de posições abertas atingido.

## Decisões de implementação

- A Fase 7 depende explicitamente das fases anteriores e não tenta aprovar uma estratégia apenas por decisão manual.
- O status `piloto` só é recomendado quando checklist, validação, robustez, paper trading e risco estão simultaneamente aprovados.
- A decisão manual foi mantida em tabela própria para auditoria e para permitir pausar ou reprovar estratégias mesmo quando as métricas forem positivas.
- Os snapshots de risco foram separados das decisões do comitê porque exposição e PnL mudam intraday, enquanto decisões de aprovação têm ciclo mais lento.
- A política inicial é conservadora e pode ser versionada sem sobrescrever histórico.

## Critérios de saída atendidos

- Nenhuma estratégia recebe recomendação de `piloto` sem checklist completo e decisão manual de aprovação.
- Há estrutura para pausar estratégia imediatamente por decisão manual ou violação de limite.
- Limites de risco ficam visíveis e auditáveis por configuração, snapshot e view operacional.
- A tela de Comitê de Estratégias pode exibir status, critérios e decisão manual em uma única fonte.
- A tela Risco e Limites pode exibir exposição, perdas, violações e alertas de desligamento.

## Próximos passos

1. Aplicar `infra/bq/14_quant_phase7_controlled_operation.sql` no BigQuery.
2. Criar rotina operacional para popular `quant_controlled_operation_risk_snapshots` a partir das posições reais ou simuladas do piloto.
3. Expor endpoints backend para `vw_quant_phase7_strategy_committee`, `vw_quant_phase7_risk_limits` e `vw_quant_phase7_shutdown_alerts`.
4. Implementar as telas **Comitê de Estratégias** e **Risco e Limites**.
5. Definir o procedimento humano de aprovação, pausa emergencial e retomada após incidente.
