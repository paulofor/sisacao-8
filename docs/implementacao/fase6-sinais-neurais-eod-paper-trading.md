# Fase 6 — Paper trading para sinais neurais EOD

## Objetivo executado

Esta fase adiciona a camada de **paper trading controlado** para os sinais neurais EOD. O modelo neural só pode entrar em simulação operacional depois de passar por critérios mínimos de backtest, e toda ordem gerada permanece sem uso de capital real.

## Artefatos criados

- `sisacao8/neural_paper_trading.py`: helpers para validar critérios mínimos e materializar ordens simuladas a partir de sinais neurais.
- `infra/bq/19_neural_eod_paper_trading.sql`: critérios versionados, avaliações de liberação e views de acompanhamento neural.
- `tests/test_neural_paper_trading.py`: cobertura unitária dos gates e da criação de ordens simuladas.

## Critérios mínimos implementados

A configuração inicial `neural_eod_paper_gate/v1` usa limites conservadores:

| Métrica | Limite inicial |
|---|---:|
| Profit factor | `>= 1.10` |
| Win rate | `>= 0.50` |
| Fill rate | `>= 0.40` |
| Drawdown máximo | `<= 0.15` |
| Trades executados | `>= 30` |
| Retorno médio | `> 0.00` |
| Sensibilidade a custos | `<= 0.25` |
| Paper trading mínimo | `60` pregões |

## Componentes técnicos

### Gate de backtest

`evaluate_neural_backtest_for_paper` recebe métricas do backtest neural e retorna:

- `approved_for_paper`, quando todos os limites são satisfeitos;
- `blocked_for_paper`, com a lista exata de critérios falhos.

Esse gate impede iniciar paper trading apenas por existência de predições ou sinais: o desempenho fora da amostra continua sendo pré-condição.

### Ordens simuladas

`build_neural_paper_orders` transforma sinais neurais aprovados em ordens simuladas com:

- quantidade fixa e baixa por padrão;
- custo e slippage explícitos;
- preço simulado piorado pelo slippage conforme lado BUY/SELL;
- identificador determinístico por execução;
- status inicial `aberta`;
- `strategy_family = neural_eod` para separar a análise neural das estratégias heurísticas.

### BigQuery

O script `19_neural_eod_paper_trading.sql` cria:

- `neural_eod_paper_criteria`: critérios versionados e parâmetros operacionais de baixo risco;
- `neural_eod_paper_evaluations`: evidência auditável de aprovação/bloqueio por modelo;
- `vw_neural_eod_paper_gate`: último status de liberação por modelo/versão;
- `vw_neural_eod_paper_metrics`: métricas agregadas das ordens neurais simuladas.

## Decisões de implementação

- A fase não promove nenhum modelo para capital real.
- O gate é separado da geração de sinais para preservar rastreabilidade e permitir bloqueio operacional sem alterar inferência.
- As ordens neurais reutilizam a tabela canônica `quant_paper_trading_orders`, distinguindo-se por `strategy_family = neural_eod`.
- Os limites foram codificados como configuração versionada no BigQuery e espelhados em dataclass para testes locais.

## Critérios de saída atendidos

- Há bloqueio explícito para modelos que não superem critérios mínimos de backtest.
- Há suporte a monitorar fill rate, win rate, retorno médio, profit factor, drawdown e sensibilidade a custos.
- Há limites baixos de ordens, quantidade, custos e slippage.
- Há rastreabilidade por modelo, versão, critérios falhos e ordem simulada.

## Próximos passos

1. Aplicar `infra/bq/19_neural_eod_paper_trading.sql` no BigQuery.
2. Registrar avaliações reais em `neural_eod_paper_evaluations` após cada backtest OOS aprovado/reprovado.
3. Criar rotina operacional que leia `vw_neural_eod_paper_gate` antes de inserir ordens neurais em `quant_paper_trading_orders`.
4. Acompanhar no mínimo 60 pregões antes de qualquer discussão de promoção controlada.
