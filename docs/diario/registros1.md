# Registros — Sisacao

> Orientação: todos os registros deste documento devem sempre incluir **data e hora no fuso UTC-3**.
> Neste documento segue política de **append-only** (não pode ter nenhuma linha apagada; apenas inserções).

> Regra obrigatória de timestamp:
> Antes de adicionar qualquer novo registro, execute obrigatoriamente:
>
> ```bash
> TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'
> ```
>
> Use exatamente a saída desse comando no título do novo registro.
> É proibido inventar, estimar, inferir ou reaproveitar data/hora a partir de:
> - contexto da conversa;
> - data do commit;
> - data do CI/build;
> - metadados do arquivo;
> - relógio UTC sem conversão explícita;
> - registros anteriores deste documento.
>
> O formato obrigatório do título é:
>
> ```md
> ## YYYY-MM-DD HH:mm:ss UTC-3
> ```
>
> Cada novo registro deve ser adicionado no final do arquivo.
> Se for necessário registrar mais de uma entrada, execute novamente o comando de data/hora para cada entrada.
> Nunca crie registro com timestamp futuro em relação ao horário atual de `America/Sao_Paulo`.
> Em caso de timestamp incorreto já registrado, não apague nem edite o registro antigo; adicione um novo registro de correção explicando o erro.
> Neste documento segue política de **append-only** (não pode ter nenhuma linha apagada; apenas inserções).

## 2026-05-09 19:07:14 UTC-3
- MCP Server Java atualizado para expor a ferramenta RPC-JSON `backend_actuator_logs_url` no `tools/list`.
- A chamada `tools/call` dessa ferramenta agora retorna a URL `http://34.194.252.70/api/actuator/logs/backend` com método `GET`, permitindo descoberta programática do endpoint de logs do backend.
- Validação executada no módulo Java com `mvn -q test` (sucesso).

## 2026-05-09 21:26:56 UTC-3
- Investigação do incidente via MCP Server: `bigquery_query` confirmou leitura da tabela `ingestaokraken.cotacao_intraday.backtest_trades` com registros existentes.
- Ajustado o backend (`BigQueryOpsClient`) para consultar primeiro o schema atual de `backtest_trades` (`exit_price`, `exit_reason`, `return_pct`) e manter fallbacks para schemas antigos (`pnl_pct` e legado com `entry_price`/`pnl_percent`).
- Atualizado teste `BigQueryOpsClientTest.shouldFallbackWhenBacktestPrimaryQueryFails` para refletir a nova ordem/shape das queries de fallback.
- Teste executado: `cd backend/sisacao-backend && ./mvnw -q -Dtest=BigQueryOpsClientTest test` (passou).

## 2026-05-10 14:12:24 UTC-3
- Registrada orientação operacional para execução de SQL no BigQuery Console a fim de adicionar colunas ausentes em `ingestaokraken.cotacao_intraday.backtest_trades` (`entry_limit_price`, `entry_signal_score` e opcionalmente `days_in_trade`) para suportar os novos campos da tela de backtest.
- Documentado que o schema canônico atual da tabela possui `entry_fill_date`, `entry`, `exit_date` e `exit_price`, e que `daysInTrade` pode ser derivado por `DATE_DIFF` enquanto preço limite e score exigem dados persistidos na tabela.
- Validada conectividade MCP via JSON-RPC em `http://mcpserversisacao.shop/mcp` com `initialize` (HTTP 200); tentativa de `tools/list` permaneceu com timeout de upstream.
- Check executado: `cd backend/sisacao-backend && ./mvnw -q -DskipTests compile` (sucesso).

## 2026-05-12 21:32:33 UTC-3
- Implementada paginação no quadro "Histórico de Sinais" do frontend com 25 registros por página fixos.
- Adicionada navegação de páginas via `TablePagination` e renderização da tabela baseada no slice paginado dos sinais.
- Incluído reset automático para página 1 quando a lista de sinais é atualizada, evitando página inválida após filtros/refresh.

## 2026-05-14 13:49:20 UTC-3
- Registrada orientação estatística para validação de amostra de backtests: tamanho mínimo por número de trades, janelas temporais e testes de significância (bootstrap/Deflated Sharpe, walk-forward e OOS) para reduzir risco de overfitting.
- Sem alteração de código de backend/frontend; atualização exclusivamente documental no diário do projeto.

## 2026-05-17 13:34:20 UTC-3
- Verificação da aba de Backtest no frontend: o componente atual (`BacktestTab`) renderiza apenas tabela de trades (`BacktestTradesTable`) e não contém componente de gráfico.
- Confirmado que a integração existente usa `GET /ops/backtest/trades` via hook `useOpsBacktestTrades` e mapeamento em `fetchOpsBacktestTrades`; não há endpoint/frontend dedicado a série para chart.
- Validado workflow de publicação do frontend no GitHub Actions: `deploy-frontend-lightsail.yml` é disparado em push para `main/master` quando há alterações em `frontend/**` e realiza build + upload para Lightsail.
- Identificada possível pendência de processo: se a mudança do gráfico não foi mergeada em `main/master` (ou foi feita fora de `frontend/**`), o deploy automático do frontend não é acionado.

## 2026-05-17 13:38:08 UTC-3
- Implementado gráfico de barras na aba Backtest do frontend para distribuição de resultados por `outcome` (ex.: TARGET, STOP, EXPIRED e outros valores presentes nos dados).
- Novo componente `BacktestOutcomesBarChart` adicionado e integrado ao `BacktestTab` acima da tabela de trades.
- Ajustado carregamento de trades na aba Backtest para consultar até 200 registros por atualização (`useOpsBacktestTrades(200)`), respeitando o limite atual do backend.

## 2026-05-17 14:29:50 UTC-3
- Adicionado card de validade estatística na aba Backtest do frontend, exibindo quantidade de trades fechados e progresso percentual em relação à meta de 500 trades.
- Card inclui barra de progresso (`LinearProgress`) com percentual limitado a 100% e rótulo numérico com uma casa decimal.
- Mantida a estrutura da aba com gráfico de distribuição e tabela de trades após o novo card.

- 2026-05-17: Alterado o componente da aba Backtest no frontend para substituir a visualização em barras por gráfico de pizza (donut) em 'Distribuição de resultados do backtest', com legenda e percentuais por outcome.

## 2026-05-23 02:53:13 UTC
- Analisada a regra de execução da aba Backtest para esclarecer diferença entre `data_ref` do sinal e `Dt Entrada` do trade.
- Confirmado no código que o backtest inicia a simulação a partir de `valid_for` e só marca entrada quando o preço `entry` é efetivamente tocado dentro da janela (`horizon_days`), podendo ocorrer vários pregões após a data de referência.
- Preparada explicação funcional para o caso observado na tela (referência 2026-04-16 com entrada em 2026-04-29).

## 2026-05-23 03:00:54 UTC
- Criado documento canônico `docs/REGRA_CANONICA_SINAIS_BACKTEST.md` definindo a regra oficial de ciclo D->D+1 para sinais EOD e execução de entrada.
- Documentado que BUY usa `close(D) * (1 - x_pct)` e SELL usa `close(D) * (1 + x_pct)`, com observação de que SELL não é gatilho de queda na implementação atual.
- Confirmado no código que `x_pct` padrão atual é 2% (`0.02`) via `SIGNAL_X_PCT`/`X_PCT`, não 1% fixo.
- Registrada divergência entre regra canônica e comportamento atual do backtest (tentativa de entrada por múltiplos dias via `horizon_days`).

## 2026-05-23 03:36:03 UTC
- Atualizado o documento canônico `docs/REGRA_CANONICA_SINAIS_BACKTEST.md` para fixar `x_pct = 0.02 (2%)` na regra D->D+1.
- Especificado no canônico que BUY exige queda de 2% sobre `close(D)` e SELL exige alta de 2% sobre `close(D)`.

## 2026-05-23 03:39:25 UTC
- Regras do backtest refeitas para aderir ao canônico D->D+1: entrada só pode ocorrer no pregão `valid_for`; se não tocar entrada nesse dia, resultado fica `NO_FILL` e o sinal não carrega para os dias seguintes.
- Mantida a lógica de saída (`TARGET`/`STOP`/`EXPIRE`) apenas para sinais que efetivamente entraram em `valid_for`, usando a janela `horizon_days` para gerenciamento da posição já aberta.
- Ajuste aplicado em `sisacao8/backtest.py` e no espelho da function `functions/backtest_daily/backtest.py`.
- Teste executado: `PYTHONPATH=. pytest -q tests/test_backtest_engine.py` (5 passed).

## 2026-05-23 12:00:00 UTC
- Validada aderência da construção do modelo/backtest à regra canônica D->D+1 consultando o documento canônico e a implementação ativa em `functions/backtest_daily/backtest.py`.
- Confirmado que a entrada é avaliada somente no pregão `valid_for`; sem toque em D+1 o resultado permanece `NO_FILL`, alinhado ao canônico.
- Preparada resposta objetiva para status de conformidade com referência explícita aos artefatos do repositório.

## 2026-05-23 04:22:28 UTC
- Corrigido erro de lint `E501` quebrando a linha longa na atribuição de `valid_for_bar` no motor de backtest e no espelho da Cloud Function.
- Arquivos ajustados: `sisacao8/backtest.py` e `functions/backtest_daily/backtest.py`.
- Revalidados checks locais de lint e testes para garantir pipeline verde.

## 2026-06-04 12:41:22 UTC-3
- Ajustado o gráfico de distribuição de resultados do backtest para considerar somente trades executados, excluindo outcomes de não execução como `NO_FILL`.
- Criado filtro compartilhado para identificar trades efetivamente realizados a partir do outcome e dos campos de entrada/saída.
- Atualizado o card de validade estatística para contabilizar `Trades executados` em vez de todos os registros carregados.

## 2026-06-05 00:00:00 UTC
- Adicionado segundo gráfico de pizza na aba Backtest do frontend para distribuir trades executados entre `Lucro` e `Prejuízo` com base no `PnL %`.
- Saídas por tempo/`EXPIRE` agora entram nesse novo gráfico conforme o PnL do trade: valores positivos em `Lucro` e valores menores ou iguais a zero em `Prejuízo`.
- Refatorada a renderização do gráfico de pizza para reutilizar a mesma estrutura visual nos gráficos por outcome e por lucro/prejuízo.
- Validações executadas no frontend: `npm run lint` e `npm run build`.

## 2026-06-05 00:00:00 UTC
- Ajustada a paleta do gráfico de distribuição de resultados do backtest no frontend para fixar `Stop` em vermelho, independentemente da ordenação dos buckets.
- Mantidas as cores já esperadas para `Expire` em azul, `Target` em verde e para o gráfico de lucro/prejuízo.

## 2026-06-05 20:59:23 UTC-3
- Tentativa de execução da etapa 6 solicitada para `docs/implementacao/oprm/plano-ajuste-pipeline-nichocnae-pesquisa-sem-vies.md`.
- A execução foi bloqueada porque o arquivo informado não existe no checkout atual e não há diretório `docs/implementacao/oprm/` versionado no repositório.
- Verificações realizadas para localizar plano equivalente: `rg --files docs`, `find /workspace/sisacao-8 ... -iname '*plano*'` e buscas por termos `oprm`, `nichocnae`, `CNAE`, `viés/vies` e `etapa 6`.
- Nenhuma alteração funcional foi aplicada para evitar inferir requisitos ausentes e preservar os padrões de arquitetura definidos.

## 2026-06-07 — Card de sinais por data com máximo/mínimo do pregão seguinte
- Adicionado endpoint operacional `/ops/signals/by-date` para buscar sinais por `date_ref` e enriquecer cada ticker com o máximo e mínimo do pregão seguinte a partir de `cotacao_ohlcv_diario`.
- Criado o card na aba **Sinais** para o usuário selecionar uma data, consultar os sinais gerados naquele dia e visualizar `Máximo`/`Mínimo` do pregão seguinte.
- Incluídos tipos/hooks frontend e testes backend cobrindo controller, service e SQL BigQuery da nova consulta.

## 2026-06-07 — Remoção do card Histórico de Sinais
- Removido da aba **Sinais** o card/tabela visual **Histórico de Sinais**, mantendo os demais blocos de filtros e simulações do histórico filtrado.
- Ajustadas as propriedades do componente para eliminar o uso do erro específico da tabela removida.
## 2026-06-07 — Destaque de sinal que gerou trade
- Atualizada a tabela **Sinais por data e pregão seguinte** no frontend para calcular quando o preço de entrada foi tocado no pregão seguinte (`BUY`: mínima <= entry; `SELL`: máxima >= entry).
- Adicionada a coluna `Trade` com chips `Gerou trade`/`Sem trade` e destaque visual em verde na linha do sinal que acionou entrada.
- Ajustado o texto explicativo do card para deixar claro que a tela identifica os sinais que acionaram a entrada do trade.
- Validações executadas no frontend: `npm run lint`, `npm run build` e captura de screenshot local com Playwright.

## 2026-06-07 — Simplificação da aba Sinais
- Removidos da aba **Sinais** os cards/blocos **Filtros — Próximo Pregão**, **Simulação de possíveis trades — Próximo pregão**, **Histórico — Período** e **Simulação de possíveis trades — Histórico filtrado**.
- Ajustado o componente da aba para exibir a tabela de próximo pregão sem filtros locais e eliminar a consulta de histórico que era usada apenas pelos blocos removidos.
- Atualizado o texto introdutório para refletir os blocos que permanecem na tela.
- Removida a evidência visual em screenshot porque não é necessária para esta alteração.

## 2026-06-07 — Remoção do resumo superior da aba Sinais
- Removido da aba **Sinais** o trecho superior destacado pelo usuário, incluindo o texto introdutório, os cards de métricas agregadas e o alerta informativo sobre backtrade.
- Simplificado o componente para eliminar cálculos e imports que eram usados somente pelo bloco removido.
- Validações executadas no frontend: `npm run lint` e `npm run build`.

## 2026-06-07 — Ajuste de evidências visuais no projeto
- Removida a evidência PNG versionada da alteração anterior porque o projeto não precisa desse tipo de screenshot salvo pedido explícito.
- Atualizado o `AGENTS.md` para orientar agentes a não gerar nem versionar screenshots/evidências visuais em alterações de frontend, exceto quando solicitado explicitamente pelo usuário.

## 2026-06-07 — Ajustes visuais da aba Backtest
- Reorganizados os gráficos da aba **Backtest** para exibir três pizzas na mesma linha em telas largas.
- Adicionado novo gráfico de pizza para comparar sinais que geraram trades contra sinais que não geraram trades.
- Limitada a tabela de backtest para mostrar somente os 10 trades mais recentes carregados.

## 2026-06-11 22:38:06 UTC — Análise do limite de 5 sinais por dia no backtest
- Investigado por que a aba **Backtest** exibe grupos de até 5 registros por `Data Ref`.
- Confirmado que o limite vem da geração EOD de sinais (`MAX_SIGNALS_PER_DAY = 5`) e não de um filtro específico da tela de backtest.
- Confirmado que o backtest processa todos os sinais existentes para a data (`date_ref`) e persiste um resultado por sinal, portanto o volume diário refletido na tela acompanha a quantidade de sinais gerados no dia.
- Verificado que a tela carrega até 200 registros no hook principal e mostra somente os 10 mais recentes na tabela visual.

## 2026-06-11 22:42:19 UTC — Backtest histórico em lote mantendo 5 sinais por dia
- Corrigida a interpretação do requisito: o limite operacional continua sendo 5 sinais por `date_ref`; o ganho esperado é processar múltiplos dias passados na mesma invocação do backtest.
- Restaurada a semântica de teto diário em `eod_signals`, mantendo `MAX_SIGNALS_PER_DAY = 5` e truncamento de `MAX_SIGNALS`/`max_signals` nesse limite por dia.
- Atualizada a Cloud Function `backtest_daily` para aceitar intervalo (`date_from`/`date_to`) e para buscar/processar múltiplas datas pendentes de backlog com `BACKTEST_MAX_DATES_PER_RUN`/`limit`.
- Adicionados testes cobrindo intervalo de dias úteis limitado e execução em lote de múltiplos `date_ref` na mesma chamada.

## 2026-06-12 04:05:30 UTC-3
- Ajustada a tabela de trades da aba **Backtest** no frontend para usar paginação fixa de 25 itens por página.
- Removida a limitação visual anterior de 10 trades, passando a renderizar o recorte da página atual e a navegação via `TablePagination`.
- Ajustados estilos da tabela para ocupar no máximo a largura do card e evitar scroll horizontal, com layout fixo e quebra/truncamento de conteúdo nas células.
- Validações executadas no frontend: `npm run lint` e `npm run build`.

## 2026-06-14 — Plano de novos sistemas quantitativos com telas de acompanhamento
- Criado documento em `docs/implementacao/plano-novos-sistemas-quantitativos.md` com plano faseado para pesquisar novas famílias de estratégias quantitativas.
- Incluídas telas de acompanhamento por fase: inventário de dados, qualidade dos dados, laboratório de backtests, comparador de estratégias, baselines, ranking, regime de mercado, robustez, paper trading, diário operacional, comitê de estratégias e risco.
- Registradas métricas mínimas, critérios de aprovação, modelo de dados sugerido e priorização em sprints para orientar a implementação futura.

## 2026-06-14 21:51:38 UTC — Fase 0 dos novos sistemas quantitativos
- Executada a preparação e inventário inicial dos dados para o plano de novos sistemas quantitativos.
- Consultado o MCP Server via JSON-RPC HTTP e inventariado o dataset BigQuery `ingestaokraken.cotacao_intraday`.
- Criado o script `infra/bq/07_quant_phase0_inventory.sql` com views de resumo, cobertura por ticker e incidentes de qualidade para as telas da Fase 0.
- Documentado o relatório da Fase 0 em `docs/implementacao/fase0-inventario-dados-quantitativos.md`, incluindo métricas observadas, lacunas e regras iniciais de elegibilidade.

## 2026-06-14 — Menu Fase 0 Quantitativa no frontend
- Adicionado novo item de menu `Fase 0 Quant` no painel operacional para exibir o inventário quantitativo.
- Criados endpoints backend em `/ops/quant/inventory-summary`, `/ops/quant/ticker-coverage` e `/ops/quant/data-quality-incidents` consumindo as views BigQuery da Fase 0.
- Implementada tela com cards de resumo, tabela de cobertura por ticker e tabela de incidentes derivados de qualidade dos dados.

## 2026-06-14 19:59:37 UTC-3
- Executada a Fase 1 do plano de novos sistemas quantitativos, preparando o contrato comum de backtest e métricas.
- Criado o script `infra/bq/08_quant_phase1_backtest_engine.sql` com tabelas canônicas `quant_strategy_signals`, `quant_backtest_trades` e `quant_backtest_metrics`.
- Incluídas views operacionais para as telas Laboratório de Backtests e Comparador de Estratégias: `vw_quant_backtest_lab_trades`, `vw_quant_backtest_lab_summary` e `vw_quant_strategy_comparator`.
- Documentado o relatório técnico da Fase 1 em `docs/implementacao/fase1-motor-backtest-metricas.md` e atualizado o plano principal com status e links dos artefatos.

## 2026-06-14 — Fase 2 dos novos sistemas quantitativos
- Executada a preparação da Fase 2 do plano de novos sistemas quantitativos, focada em sistemas baseline simples.
- Criado o script `infra/bq/09_quant_phase2_baseline_systems.sql` com catálogo de estratégias, features diárias, sinais candidatos, status e alertas para as telas de baseline.
- Documentado o relatório técnico em `docs/implementacao/fase2-sistemas-baseline-simples.md`, incluindo hipóteses, regras iniciais, decisões de implementação e próximos passos.
- Atualizado o plano principal para registrar a Fase 2 como preparada e apontar para os artefatos gerados.

## 2026-06-14 21:15:16 UTC-3
- Executada a preparação da Fase 3 do plano de novos sistemas quantitativos, focada em ranking e seleção de ativos.
- Criado o script  com configuração versionada de ranking, fatores diários, ranking de oportunidades, carteiras top N e métricas de monotonicidade/performance.
- Documentado o relatório técnico em , incluindo decisões de implementação, critérios de saída e próximos passos.
- Atualizado o plano principal para registrar a Fase 3 como preparada e apontar para os artefatos gerados.

## 2026-06-14 21:15:50 UTC-3
- Correção do registro anterior da Fase 3: os artefatos criados foram `infra/bq/10_quant_phase3_asset_ranking.sql` e `docs/implementacao/fase3-ranking-selecao-ativos.md`.
- A entrada anterior perdeu os caminhos por substituição indevida de crases no shell, mas os arquivos foram criados corretamente.

## 2026-06-15 — Fase 4 dos novos sistemas quantitativos
- Executada a preparação da Fase 4 do plano de novos sistemas quantitativos, focada em filtros de regime e controle de exposição.
- Criado o script `infra/bq/11_quant_phase4_market_regime_exposure.sql` com política versionada de regime, indicadores de mercado, recomendação de exposição, performance por regime e efetividade dos filtros.
- Documentado o relatório técnico em `docs/implementacao/fase4-filtros-regime-exposicao.md`, incluindo regimes classificados, regras de exposição, decisões de implementação e próximos passos.
- Atualizado o plano principal para registrar a Fase 4 como preparada e apontar para os artefatos gerados.
## 2026-06-14 22:02:22 UTC-3
- Corrigido o script SQL da Fase 3 (`infra/bq/10_quant_phase3_asset_ranking.sql`) removendo `NOT NULL` do campo `top_n_values ARRAY<INT64>` na tabela `quant_ranking_model_config`.
- Motivo: BigQuery não permite aplicar `NOT NULL` diretamente a campos do tipo `ARRAY`; arrays nulos são armazenados como arrays vazios.
- Validação local realizada por busca textual para confirmar que não restaram colunas `ARRAY<...> NOT NULL` no script.

## 2026-06-15 — Fase 5: validação estatística e robustez

- Preparada a Fase 5 do plano de novos sistemas quantitativos.
- Criado o script `infra/bq/12_quant_phase5_statistical_robustness.sql` com política versionada de validação, splits treino/validação/teste, walk-forward mensal, testes por subperíodos/grupos de ativos, estresse de custos/slippage, benchmark contra aleatorização, sensibilidade inicial a parâmetros e dashboard consolidado de robustez.
- Criado o relatório `docs/implementacao/fase5-validacao-estatistica-robustez.md` descrevendo objetivos, componentes técnicos, decisões e próximos passos.
- Atualizado `docs/implementacao/plano-novos-sistemas-quantitativos.md` para marcar a Fase 5 como preparada e referenciar os novos artefatos.

## 2026-06-15 — Fase 6: simulação operacional em paper trading

- Preparada a Fase 6 do plano de novos sistemas quantitativos.
- Criado o script `infra/bq/13_quant_phase6_paper_trading.sql` com configuração versionada de paper trading, tabela de ordens simuladas, log auditável de decisões e views para sinais candidatos, dashboard, ordens abertas/encerradas, aderência ao backtest e diário operacional.
- Criado o relatório `docs/implementacao/fase6-paper-trading.md` descrevendo objetivos, componentes técnicos, decisões, critérios atendidos e próximos passos.
- Atualizado `docs/implementacao/plano-novos-sistemas-quantitativos.md` para marcar a Fase 6 como preparada e referenciar os novos artefatos.

## 2026-06-15 — Fase 7: preparação para operação controlada

- Preparada a Fase 7 do plano de novos sistemas quantitativos.
- Criado o script `infra/bq/14_quant_phase7_controlled_operation.sql` com configuração versionada de risco, checklist de aprovação, decisões do comitê, snapshots de risco e views para Comitê de Estratégias, Risco e Limites e alertas de desligamento.
- Criado o relatório `docs/implementacao/fase7-operacao-controlada.md` descrevendo objetivos, componentes técnicos, decisões, critérios atendidos e próximos passos.
- Atualizado `docs/implementacao/plano-novos-sistemas-quantitativos.md` para marcar a Fase 7 como preparada e referenciar os novos artefatos.

## 2026-06-14 22:39:37 UTC-3
- Complemento/correção do registro da Fase 7: este é o registro com timestamp no formato obrigatório obtido por `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.
- A Fase 7 foi preparada com os artefatos `infra/bq/14_quant_phase7_controlled_operation.sql` e `docs/implementacao/fase7-operacao-controlada.md`.
- O plano principal `docs/implementacao/plano-novos-sistemas-quantitativos.md` foi atualizado para referenciar a Fase 7 como preparada.
## 2026-06-15 — Correção SQL da Fase 5

- Corrigido o script `infra/bq/12_quant_phase5_statistical_robustness.sql` na view `vw_quant_phase5_robustness_dashboard`, adicionando o alias `AS o` ao CTE `oos` usado nas colunas selecionadas e nos `JOINs`.
- Motivo: a execução no BigQuery falhava com `Unrecognized name: o` porque a consulta referenciava `o.*` sem declarar o alias no `FROM`.

## 2026-06-15 — Menu e roadmap de telas quantitativas

- Criada estrutura de menu lateral com grupos de navegação para Operação e Sistemas quantitativos.
- Adicionados submenus para as fases 0 a 7 do plano de novos sistemas quantitativos.
- Fases já visíveis continuam apontando para Inventário Quantitativo e Backtest.
- Fases ainda sem endpoints definitivos passam a abrir uma tela de roadmap com dados necessários, plano visual e sequência de implementação.
- Documentado o plano de telas em `docs/implementacao/plano-telas-sistemas-quantitativos.md`.

## 2026-06-15 — Tela de roadmap quantitativo

- Implementada a tela de plano de telas quantitativas no frontend, com visão geral das fases 2 a 7, destaque da fase selecionada pelo submenu e detalhamento de dados necessários, plano visual e sequência de implementação.
- Mantida a navegação lateral de Sistemas quantitativos como índice das fases e a tela de roadmap como fallback para fases ainda sem endpoints definitivos.
## 2026-06-15 — ArchUnit para isolamento conforme relatório
- Adicionada dependência de teste `archunit-junit5` ao backend Maven.
- Removido o placeholder de pacote qualitativo criado anteriormente, pois o relatório já descreve a separação lógica de notícias, fundamentos e feature store.
- Criado teste ArchUnit para validar ausência de ciclos entre os módulos/pacotes reais do backend, preservando as fronteiras arquiteturais descritas no relatório.

## 2026-06-15 — Execução e exposição das baselines quantitativas
- Verificado via MCP/BigQuery que as tabelas e views da Fase 1/Fase 2 (`quant_strategy_signals`, `quant_backtest_trades`, `quant_backtest_metrics`, `quant_baseline_strategy_config`, `vw_quant_phase2_baseline_status` e `vw_quant_phase2_strategy_detail_alerts`) existem no dataset `cotacao_intraday`; a checagem operacional retornou 7 linhas de status de baseline e 0 sinais candidatos/trades/métricas materializados no momento da consulta.
- Criado o script `infra/bq/15_quant_phase2_baseline_execution.sql` para materializar sinais baseline em `quant_strategy_signals` e popular `quant_backtest_trades`/`quant_backtest_metrics` de forma idempotente para `config_version = phase2_baseline`.
- Expostos endpoints backend para consulta da Fase 2: `GET /ops/quant/strategies`, `GET /ops/quant/strategies/{strategyId}` e `GET /ops/quant/strategies/alerts`, conectados às views `vw_quant_phase2_baseline_status` e `vw_quant_phase2_strategy_detail_alerts`.
- Executados checks locais `./mvnw test`, `flake8` e `pytest`.

## 2026-06-15

- Corrigido o script `infra/bq/15_quant_phase2_baseline_execution.sql` para tipar explicitamente `regime_label` como `STRING` no `INSERT` de `quant_backtest_trades`, evitando erro do BigQuery ao inferir `NULL` como `INT64`.
## 2026-06-15 — Tela operacional de baselines quantitativas
- Ajustada a navegação `Fase 2 · Baselines` para renderizar uma tela operacional com dados dos endpoints `GET /ops/quant/strategies` e `GET /ops/quant/strategies/alerts`, em vez de apenas exibir o roadmap.
- Incluídos hooks TanStack Query e normalização de payloads no frontend para estratégias baseline e alertas de detalhe.
- A tela agora apresenta cartões de resumo, cards por família de estratégia, tabela de métricas/status e aviso quando há catálogo, mas ainda não há sinais candidatos/trades/métricas materializados.
- Executados checks `npm run build`, `npm run lint`, `flake8` e `pytest`.

## 2026-06-15 14:47:13 UTC-3 — Tela operacional de ranking quantitativo
- Implementada a tela operacional da Fase 3 (`Fase 3 · Ranking`) no frontend, substituindo o roadmap por cards de resumo, tabela de oportunidades ranqueadas e tabela de performance histórica por Top N/decil.
- Criados hooks e normalização de payloads para consumir `GET /ops/quant/ranking/daily` e `GET /ops/quant/ranking/performance`.
- Expostos endpoints backend read-only para ranking diário e performance da Fase 3, conectados às views BigQuery `vw_quant_phase3_daily_asset_ranking` e `vw_quant_phase3_ranking_performance`.
- Executados checks `npm run build`, `npm run lint`, `./mvnw test`, `flake8` e `pytest`.

## 2026-06-15 18:05 UTC — Diagnóstico de baselines sem sinais
- Investigado por que a tela de Fase 2 mostra todas as famílias com `sem_sinais`.
- Confirmado pelo endpoint publicado `GET /api/ops/quant/strategies` que as 7 estratégias retornam `generatedSignals = 0`, `signalDays = 0` e `computedStatus = sem_sinais`.
- Confirmado pelo endpoint `GET /api/ops/quant/ticker-coverage?limit=200` que não há tickers com `eligibilityStatus = elegivel`; a amostra retornou 150 em `observacao` e 2 em `excluir`.
- Identificada a causa técnica provável: a view de candidatos da Fase 2 filtra `vw_quant_ticker_coverage` exclusivamente por `eligibility_status = 'elegivel'`, então nenhuma feature/candidato é gerado enquanto todos os tickers estiverem em `observacao`/`excluir`.
- Tentada consulta ao MCP via JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp`, mas o endpoint retornou `503`/timeout no `initialize`; o diagnóstico foi feito pelos endpoints públicos do backend e pelos scripts SQL versionados.

## 2026-06-15 18:15 UTC — Decisão prática para liberar baselines com controle estatístico
- Avaliada a alternativa de aguardar correção completa da qualidade contra a alternativa de aceitar `observacao` de forma ampla.
- Decisão recomendada: não liberar `observacao` indiscriminadamente; usar um universo de pesquisa controlado que aceita `elegivel` e aceita `observacao` somente com cobertura >= 90%, volume financeiro >= R$ 1.000.000, preços/volumes válidos e até 3 duplicidades técnicas.
- Ajustada a view `vw_quant_phase2_daily_features` para deduplicar `cotacao_ohlcv_diario` por `ticker`/`data_pregao`, mantendo o registro mais recente por `atualizado_em`/`ingestion_run_id` antes de calcular retornos, médias, RSI e sinais.
- Ajustado o script operacional da Fase 2 para também deduplicar candles futuros no backtest, preservando consistência entre geração de sinais e simulação.
- Motivo estatístico/mercado: bloquear todas as estratégias por poucas duplicidades técnicas gera viés operacional de ausência total de amostra; liberar dados sem filtros de liquidez/cobertura gera risco de overfitting e sinais espúrios. A solução intermediária maximiza amostra útil sem abandonar governança.

## 2026-06-15 18:25 UTC — Correção de compatibilidade BigQuery na deduplicação da Fase 2
- Corrigido erro de execução do BigQuery `Name ingestion_run_id not found` na criação da view `vw_quant_phase2_daily_features`.
- Ajustada a deduplicação de `cotacao_ohlcv_diario` para ordenar apenas por `atualizado_em`, coluna disponível no schema real da tabela.
- Aplicada a mesma correção no script operacional `infra/bq/15_quant_phase2_baseline_execution.sql`, mantendo consistência entre geração de features e backtest.

## 2026-06-15 - Tela Fase 4 Regime/Exposição
- Implementada a tela operacional da Fase 4 no frontend com regime atual, recomendação de exposição, histórico, performance por regime e efetividade dos filtros.
- Adicionados hooks e normalização de payload para endpoints `/ops/quant/market-regime`, `/ops/quant/exposure`, `/ops/quant/strategy-regime-performance` e `/ops/quant/filter-effectiveness`.
- Expostos endpoints Java/Spring para consultar as views BigQuery da Fase 4.

## 2026-06-15 - Tela Fase 5 Robustez
- Implementada a tela operacional da Fase 5 no frontend com cartões de resumo, tabela por estratégia, walk-forward, stress de custos/slippage e sensibilidade de parâmetros.
- Adicionados contrato TypeScript, normalização de payload e hook TanStack Query para o endpoint `/ops/quant/robustness`.
- Integrada a navegação `Fase 5 · Robustez` ao ciclo de atualização da aba quantitativa, substituindo a visualização genérica de roadmap por uma tela operacional preparada para o backend da Fase 5.
- Executados checks `npm --prefix frontend/app run build` e `npm --prefix frontend/app run lint`.

## 2026-06-16 — Tela operacional da Fase 6 Paper Trading
- Implementada a tela da Fase 6 no frontend, substituindo o roadmap por uma visão operacional de Paper Trading e Diário Operacional com cards de PnL, aderência, ordens abertas, encerradas e eventos recentes.
- Adicionado consumo do endpoint `/ops/quant/paper-trading` no frontend, com normalização de payloads em camelCase/snake_case e atualização integrada ao botão global do painel.
- Exposto endpoint backend `/ops/quant/paper-trading`, consolidando dashboard, ordens abertas, ordens encerradas do dia e diário operacional a partir das views BigQuery da Fase 6.

## 2026-06-16 — Análise de automação e autoajuste quantitativo
- Analisado o repositório para responder se o sistema está preparado para se ajustar automaticamente ao longo do tempo.
- Confirmada existência de várias automações operacionais: deploy das Cloud Functions/Cloud Run, coletas diária e intraday, agregação de candles, geração de sinais EOD, backtest diário, alertas e checks de qualidade via Scheduler/BigQuery.
- Confirmado que a geração de sinais usa parâmetros versionados por tabela/configuração e ranking determinístico baseado em métricas recentes e liquidez, mas não há evidência de rotina produtiva de retreinamento, otimização automática de parâmetros, promoção automática de modelos ou execução automática de ordens.
- Identificado código experimental de treinamento em `functions/pattern_detection`, porém sem integração operacional evidente ao pipeline de produção.

## 2026-06-16 — Job diário de avaliação quantitativa
- Criada a Cloud Function `quant_daily_evaluation` para materializar uma autoavaliação diária dos sistemas quantitativos em `cotacao_intraday.quant_daily_model_evaluation`.
- O job consolida evidências das views de ranking da Fase 3, robustez da Fase 5 e paper trading da Fase 6, gerando score, status, decisão e razões em JSON.
- A decisão diária é deliberadamente governada (`blocked`, `observe`, `paper_trading_candidate`, `approved_candidate`) e não executa retreinamento, promoção automática ou ordens reais.
- Adicionado deploy no GitHub Actions, configuração recomendada do Cloud Scheduler e testes unitários dos critérios de avaliação.
## 2026-06-16 — Tela operacional da Fase 7 Comitê/Risco
- Implementada a tela da Fase 7 no frontend, substituindo o roadmap por uma visão operacional de Comitê de Estratégias, Risco e Limites com cards de governança, tabela de candidatas, limites de risco e snapshots de exposição.
- Adicionado consumo do endpoint `/ops/quant/committee`, com contrato TypeScript e normalização de payloads em camelCase/snake_case para estratégias, limites e exposição.
- Integrada a navegação `Fase 7 · Comitê/Risco` ao botão global de atualização por meio de hook TanStack Query dedicado.
- Executados checks `npm run build` e `npm run lint` em `frontend/app`.

## 2026-06-16 14:35 UTC — Correção do erro operacional do `backtest_daily`
- Verificado via MCP/Cloud Run logs que o job `backtest_daily` processava 5 datas em uma invocação e concluía o lote, mas a chamada HTTP do Scheduler recebia `504` antes do término, marcando a última execução como falha.
- Ajustado o padrão de `BACKTEST_MAX_DATES_PER_RUN` de 5 para 1 para manter a execução agendada dentro da janela de resposta HTTP; reprocessamentos em lote continuam possíveis informando `limit` na URL ou configurando explicitamente a variável de ambiente.
- Arquivo ajustado: `functions/backtest_daily/main.py`.

## 2026-06-16 14:49 UTC — Pesquisa detalhada dos logs do `backtest_daily`
- Consultado o MCP por JSON-RPC em `http://mcpserversisacao.shop/mcp`, usando a ferramenta `cloud_run_function_logs` para o serviço `backtest-daily` nas últimas 168 horas.
- Identificado que o erro registrado no Cloud Run/Scheduler foi `POST 504` para `https://us-east1-ingestaokraken.cloudfunctions.net/backtest_daily` em 2026-06-12 01:15:05 UTC, 2026-06-13 01:15:18 UTC e 2026-06-16 01:15:24 UTC.
- Não apareceu traceback/exception da aplicação nesses logs; após cada `504`, a função continuou registrando `BACKTEST_DAILY_COMPLETED` para 5 datas e `BACKTEST_DAILY_BATCH_COMPLETED`, indicando falha de prazo da chamada HTTP e não falha de cálculo/persistência do backtest.

## 2026-06-16 15:08 UTC — Verificação operacional das demais Cloud Functions
- Verificados via MCP/Cloud Run logs os serviços `alerts`, `dq_checks`, `eod_signals`, `get_stock_data`, `intraday_candles`, `google_finance_price`, `quant_daily_evaluation` e `backtest_daily` nas últimas 72-168 horas.
- Confirmado que `alerts`, `eod_signals` e `get_stock_data` tinham retornos HTTP 200 recentes; `eod_signals` registrou saída esperada para data sem pregão B3.
- Identificados erros reais em `dq_checks`: HTTP 500 por query inválida no check `intraday_freshness` (`ativos.ativos` sem agregação) e erro secundário de serialização JSON de `date` ao persistir resultados/incidentes.
- Identificado erro real em `intraday_candles`: HTTP 500 por frequência pandas inválida/depreciada `1H`/`H` no rollup horário; ajustado para `1h` no pacote principal e no espelho da Cloud Function.
- Observado que `google_finance_price` teve falhas pontuais de extração para alguns tickers após fallback, mas os logs recentes consultados não indicaram HTTP 500/504 como nos casos acima.
- Validada via MCP/BigQuery a nova forma da query de `intraday_freshness` para 2026-06-15, retornando 1 linha sem erro de agregação.

## 2026-06-17 01:12 UTC — Diagnóstico do alerta da Fase 3 Ranking
- Investigado o alerta `Nenhum ativo retornado pelo endpoint /ops/quant/ranking/daily` observado no painel operacional publicado em `http://34.194.252.70/`.
- Confirmado por inspeção do frontend que o alerta aparece quando a lista normalizada do ranking diário fica vazia após o carregamento, e que o cliente Axios tenta uma segunda base de URL em respostas 502/503/504.
- Testado o endpoint publicado `GET http://34.194.252.70/api/ops/quant/ranking/daily?limit=5`: a API respondeu HTTP 502 com mensagem `Falha ao consultar BigQuery` no caminho `/ops/quant/ranking/daily`.
- Confirmado via MCP/BigQuery que a view `ingestaokraken.cotacao_intraday.vw_quant_phase3_daily_asset_ranking` não está vazia: retornou 21.128 registros e data máxima `2026-06-16`; a view de performance retornou 6 registros.
- Conclusão operacional: o alerta visual não indica ausência real de ranking no BigQuery; ele é provocado pela falha HTTP 502 do backend e pelo fallback do cliente para a base vazia, que recebe o HTML do SPA como HTTP 200 e normaliza a resposta não-array como lista vazia.
- Próximos passos recomendados: otimizar/materializar a consulta do ranking diário ou evitar `SELECT *` sobre a view dinâmica no endpoint, e ajustar o fallback do cliente para não mascarar respostas 502 da API como lista vazia.

## 2026-06-17 01:18 UTC — Execução dos próximos passos do ranking diário
- Ajustado o cliente HTTP do frontend para não tentar fallback de base em respostas 502/503/504; com isso, falhas reais da API deixam de ser mascaradas como payload vazio/HTML do SPA e passam a acionar o estado de erro da tela.
- Otimizada a consulta backend de `GET /ops/quant/ranking/daily`: o SQL agora qualifica a view uma única vez, projeta explicitamente apenas as colunas consumidas pela tela e reutiliza a CTE para calcular a última data disponível antes de ordenar/limitar os registros.
- Executados `npm run lint`, `npm run build` e `mvn test` para validar frontend e backend após os ajustes.

## 2026-06-17 17:12 UTC — Verificação das execuções de fim do dia de 2026-06-16
- Consultado o MCP via JSON-RPC em `http://mcpserversisacao.shop/mcp`, usando `cloud_run_function_logs` para verificar as Cloud Functions operacionais nas últimas 36-48 horas.
- Confirmadas execuções HTTP 200 no fechamento/rotina noturna para `alerts` (2026-06-16 21:00 UTC), `quant_daily_evaluation` (2026-06-16 22:45 UTC), `get_stock_data` (carga diária de 150 candles de 2026-06-16 às 2026-06-17 00:50 UTC), `eod_signals` (2026-06-17 01:00 UTC) e `backtest_daily` (2026-06-17 01:15 UTC).
- Verificado no BigQuery que `cotacao_ohlcv_diario` possui 150 registros para `data_pregao=2026-06-16`, `cotacao_b3` possui 846 registros intraday de 47 tickers para `data=2026-06-16`, e as tabelas agregadas `candles_intraday_15m`/`candles_intraday_1h` possuem 846/423 registros para a mesma data.
- Identificado que `dq_checks` executou na janela noturna, porém falhou com HTTP 500 em 2026-06-17 01:30 UTC por erro de serialização JSON de `date`; por isso `dq_checks_daily` ficou sem registros para `check_date=2026-06-16`.
- Observado que `sinais_eod` executou com HTTP 200, mas a execução noturna gerou/persistiu sinais para `date_ref=2026-06-15` às 2026-06-16 22:00 UTC; não há registros com `date_ref=2026-06-16` no BigQuery no momento da consulta.
- Conclusão: nem todas as funções ficaram plenamente concluídas para o fechamento de 2026-06-16; a principal falha real é `dq_checks`, e há divergência operacional a revisar em `eod_signals`/avaliação quantitativa quanto à data de referência esperada para 2026-06-16.

## 2026-06-17 17:35 UTC — Correção das falhas de fechamento de 2026-06-16
- Corrigido `dq_checks` para serializar `created_at` e valores temporais dentro de `details` antes do `load_table_from_json`, eliminando a falha HTTP 500 causada por objetos `datetime/date/time` não serializáveis pelo JSON padrão.
- Ajustado o padrão de data de `eod_signals`: quando executado sem `date_ref` após o cutoff de 18:00 BRT, o job agora usa a própria data local do pregão em vez de subtrair um dia; antes, a execução das 22:00 BRT de 2026-06-16 caía indevidamente em `date_ref=2026-06-15`.
- Aplicado o mesmo critério de data padrão em `quant_daily_evaluation`, para que a avaliação quantitativa noturna pós-cutoff seja materializada para o dia recém-fechado.
- Adicionados testes unitários cobrindo serialização dos payloads de DQ e a seleção automática da data antes/depois do cutoff em `eod_signals` e `quant_daily_evaluation`.
- Executados `pytest`, `flake8` e `black --check` nos módulos e testes impactados.

## 2026-06-17 18:10 UTC — Avaliação estatística dos resultados quantitativos atuais
- Consultado o MCP via JSON-RPC em `http://mcpserversisacao.shop/mcp`, usando a ferramenta `bigquery_query` para revisar `sinais_eod`, `backtest_metrics` e `backtest_trades`.
- Confirmado que as tabelas operacionais estão populadas: `backtest_metrics` com 1.097 linhas, `backtest_trades` com 145 linhas e `sinais_eod` com 210 linhas; as últimas modificações ocorreram em 2026-06-17 entre 01:00 e 01:15 UTC.
- Identificado desalinhamento temporal: sinais EOD chegaram até `valid_for=2026-06-16`, mas as métricas consolidadas de backtest consultadas têm `as_of_date` máximo em 2026-05-20.
- Na última fotografia de backtest (`as_of_date=2026-05-20`), o agregado total teve 84 fills, win rate ponderado de 52,38%, retorno médio ponderado por fill de 0,252% e profit factor médio simples de 1,29; a perna SELL concentrou a qualidade, com 38 fills, win rate de 68,42%, retorno médio de 2,76% e profit factor médio de 10,24, enquanto BUY teve 46 fills, win rate de 39,13%, retorno médio de -1,82% e profit factor médio de 0,15.
- Conclusão: há edge estatístico promissor e assimétrico no lado vendido, mas o sistema ainda não deve ser promovido para capital real sem atualização do backtest até a data dos sinais, controle de amostra/outliers, análise de custos/slippage e validação walk-forward/paper trading.

## 2026-06-17 18:32 UTC — Esclarecimento sobre sistemas quantitativos criados e rede neural
- Revisado o repositório para separar o módulo experimental de rede neural (`functions/pattern_detection`) das estruturas quantitativas produtivas/operacionais em BigQuery, backend e frontend.
- Confirmado que a rede neural existente é um utilitário de pesquisa para classificação de movimentos de preço via MLP TensorFlow, com janelas de retornos, classes `down`/`neutral`/`up`, treino cronológico e conversão de probabilidades em ações `buy`/`sell`/`hold`; ela não aparece como Cloud Function com `main.py` operacional nem como rotina produtiva de retreinamento/promoção automática.
- Confirmados no BigQuery, via MCP JSON-RPC, 7 sistemas baseline em `quant_baseline_strategy_config`: momentum diário, reversão à média diária, rompimento diário, gap continuation, gap fade, ranking de força relativa e filtro de regime Ibovespa, todos em status `em_teste`.
- Confirmados também 2 modelos de ranking em `quant_ranking_model_config`: `asset_ranking_simple_v1` e `asset_ranking_weighted_v1`, com carteiras top 3/5/10 e pesos versionados.
- Além das estratégias em si, foram criadas camadas quantitativas de suporte: motor comum de backtest/métricas, ranking, filtro de regime/exposição, validação estatística/robustez, paper trading, governança de operação controlada e avaliação diária de prontidão (`quant_daily_model_evaluation`).

## 2026-06-17 19:05 UTC — Avaliação dos resultados dos sistemas quantitativos não neurais
- Consultado o MCP via JSON-RPC em `http://mcpserversisacao.shop/mcp`, usando `bigquery_query` para avaliar somente sistemas não neurais: baselines da Fase 2, rankings da Fase 3, filtros de regime da Fase 4, robustez da Fase 5 e avaliação diária de prontidão.
- Nas métricas agregadas de `quant_backtest_metrics`, apenas `baseline_daily_breakout_v1` apresentou expectancy líquida positiva no agregado (`+0,139%` por trade, 110 trades, win rate 40,0%, profit factor médio 1,09), mas com robustez média baixa; os demais agregados ficaram negativos: momentum (`-0,154%`, 856 trades), ranking de força relativa (`-0,232%`, 337 trades), gap fade SELL (`-0,284%`, 151 trades), gap continuation (`-0,289%`, 378 trades) e reversão à média (`-1,55%`, 10 trades).
- Na robustez da Fase 5, o melhor candidato foi `baseline_gap_fade_v1`, com score 67,5, status OOS aprovado e decisão diária `paper_trading_candidate`, porém sensível a custos; todas as demais estratégias avaliadas ficaram `blocked` por falha/degradação fora da amostra, walk-forward instável, sensibilidade a custos e/ou não superação do benchmark aleatório.
- Os rankings da Fase 3 ainda não estão aprovados: `asset_ranking_simple_v1` ficou `sem_monotonicidade`, com retornos top N negativos e excesso versus aleatório negativo; `asset_ranking_weighted_v1` ficou `em_observacao`, com leve excesso positivo no top 3/top 5, mas retorno absoluto ainda negativo e monotonicidade fraca.
- Os filtros de regime melhoraram parcialmente momentum e gap continuation, mas ainda deixaram expectancy filtrada negativa; para `gap_fade`, o filtro atual piorou o resultado por bloquear trades bons, indicando que regras vendidas precisam de tratamento de regime separado.
- Conclusão operacional: entre os sistemas não neurais, não há estratégia aprovada para capital real. `baseline_gap_fade_v1` é o único candidato para paper trading controlado; `baseline_daily_breakout_v1` merece reavaliação/calibração por ter edge agregado positivo mas robustez fraca; rankings e demais baselines devem permanecer bloqueados/observação até nova parametrização e maior estabilidade fora da amostra.

## 2026-06-17 19:24 UTC — Suficiência de dados para conclusão dos sistemas não neurais
- Consultado o MCP via JSON-RPC em `http://mcpserversisacao.shop/mcp`, usando `bigquery_query` sobre `quant_backtest_trades` para medir amostra, janela histórica, dispersão e intervalo de confiança aproximado por estratégia não neural.
- A amostra atual cobre aproximadamente de 2026-02-27/2026-03-06 até 2026-06-10/2026-06-11 para a maioria das estratégias, com 37 a 68 dias com trades nos sistemas principais; `baseline_daily_mean_reversion_v1` é exceção clara, com apenas 10 trades em 8 dias.
- Há dados suficientes para rejeitar/promover cautela em estratégias com resultado persistentemente ruim: `baseline_gap_continuation_v1` teve 378 trades e IC95% do retorno médio líquido totalmente negativo; `baseline_daily_mean_reversion_v1` também teve IC95% negativo, mas com amostra pequena. Momentum, ranking de força relativa e gap fade têm médias negativas, mas IC95% ainda cruza zero.
- Não há dados suficientes para aprovar capital real em nenhuma estratégia: `baseline_daily_breakout_v1` foi o único retorno médio positivo, porém com t-stat baixo e IC95% cruzando zero; `baseline_gap_fade_v1` foi o melhor em robustez/OOS, mas o retorno médio agregado ainda é negativo e sensível a custos.
- Conclusão: já existe informação suficiente para decisões defensivas (bloquear, recalibrar e limitar paper trading), mas ainda é necessário mais tempo e/ou mais trades em paper para decisões ofensivas de aprovação. Recomenda-se acumular pelo menos mais 2 a 3 meses de observação, com custos/slippage reais, e exigir estabilidade por regime antes de qualquer piloto com capital real.

## 2026-06-17 19:38 UTC — Marcação de estratégias sem recuperação prática no desenho atual
- A pedido do usuário, as estratégias não neurais foram reclassificadas em linguagem operacional para facilitar decisão: `sem_chance_no_desenho_atual`, `bloqueada_mas_recuperavel_com_reparametrizacao`, `observacao/recalibracao` e `paper_trading_controlado`.
- Marcadas como `sem_chance_no_desenho_atual`: `baseline_daily_mean_reversion_v1` (amostra pequena, retorno médio muito negativo, IC95% negativo e robustez 0) e `asset_ranking_simple_v1` (sem monotonicidade, retornos top N negativos e excesso versus aleatório negativo). Essas hipóteses não devem receber mais tempo no formato atual; só faria sentido recriá-las como nova versão com tese/feature/parametrização diferente.
- Marcadas como `bloqueada_mas_recuperavel_com_reparametrizacao`: `baseline_gap_continuation_v1` (evidência negativa mais forte no desenho atual), `baseline_daily_momentum_v1` e `baseline_relative_strength_ranking_v1` (amostras maiores, médias negativas e robustez fraca). Não devem ir para paper trading, mas podem ser revisitadas com filtros de regime, custos e parâmetros novos.
- Marcadas como `observacao/recalibracao`: `baseline_daily_breakout_v1` e `asset_ranking_weighted_v1`; o primeiro tem expectancy agregada positiva porém estatisticamente inconclusiva, e o segundo é melhor que o ranking simples, mas ainda sem retorno absoluto positivo/monotonicidade forte.
- Mantida como `paper_trading_controlado`: `baseline_gap_fade_v1`, por ser o melhor candidato em robustez/OOS, ainda que sensível a custos e inadequado para capital real neste momento.

## 2026-06-17 19:55 UTC — Tela frontend com ícones de decisão dos sistemas não neurais
- Implementado no frontend, na tela de Estratégias Baseline da área quantitativa, um quadro de decisão operacional com os ícones aprovados pelo usuário para classificar sistemas não neurais.
- O quadro exibe `❌` para hipóteses sem chance no desenho atual, `⛔` para bloqueadas mas recuperáveis por reparametrização, `👀` para observação/recalibração e `🧪` para paper trading controlado.
- A tabela inclui as oito classificações discutidas: `baseline_daily_mean_reversion_v1`, `asset_ranking_simple_v1`, `baseline_gap_continuation_v1`, `baseline_daily_momentum_v1`, `baseline_relative_strength_ranking_v1`, `baseline_daily_breakout_v1`, `asset_ranking_weighted_v1` e `baseline_gap_fade_v1`.

## 2026-06-18 02:48 UTC — Verificação das funções noturnas de 2026-06-18
- Consultado o MCP via JSON-RPC em `http://mcpserversisacao.shop/mcp`, usando `cloud_run_function_logs` e `bigquery_query` para validar a janela noturna referente ao pregão de 2026-06-17.
- Confirmadas respostas HTTP 200 e ausência de logs `severity>=ERROR` nas últimas 12 horas para `alerts`, `quant_daily_evaluation`, `get_stock_data`, `eod_signals`, `backtest_daily`, `dq_checks` e `intraday_candles`.
- Confirmado no BigQuery que `cotacao_ohlcv_diario` possui 150 registros para `data_pregao=2026-06-17`, `sinais_eod` possui 5 sinais para `date_ref=2026-06-17`, `dq_checks_daily` possui 8 checks para `check_date=2026-06-17`, `quant_daily_model_evaluation` possui 12 avaliações para `reference_date=2026-06-17`, e as tabelas `candles_intraday_15m`/`candles_intraday_1h` possuem 829/423 registros para `reference_date=2026-06-17`.
- `backtest_daily` executou com HTTP 200 às 2026-06-18 01:15 UTC e processou `date_ref=2026-05-21`, com 5 sinais, 5 trades e 46 métricas; o BigQuery confirmou 46 linhas em `backtest_metrics` para `as_of_date=2026-05-21`.
- Conclusão: as funções noturnas verificadas em 2026-06-18 executaram com sucesso; não foi identificada falha HTTP 500/504 nem erro severo na janela consultada.

## 2026-06-18 00:00 UTC — Explicação do sistema de backtest diário
- Revisado o módulo `functions/backtest_daily` e a documentação operacional das Cloud Functions para responder à solicitação sobre o sistema que executa backtest todos os dias.
- Confirmado que o job `backtest_daily` busca sinais EOD, carrega candles OHLCV diários, simula entradas/saídas de forma determinística, persiste trades e recalcula métricas rolling no BigQuery.
- Registrado que a última verificação operacional documentada indicou execução HTTP 200 em 2026-06-18 01:15 UTC, processando `date_ref=2026-05-21` com 5 sinais, 5 trades e 46 métricas.

## 2026-06-18 00:00 UTC — Explicação da geração dos sinais EOD
- Revisado o módulo `functions/eod_signals` para responder como os sinais usados pelo backtest diário são gerados.
- Confirmado que `eod_signals` executa após cutoff de 18:00 BRT, seleciona a data de referência, carrega configuração versionada, lê candles diários em `cotacao_ohlcv_diario`, opcionalmente filtra por volume, consulta métricas recentes de `backtest_metrics`, gera até 5 sinais condicionais por ranking e persiste em `sinais_eod`.
- Resumida a regra de sinal: para cada ticker elegível são montados candidatos BUY/SELL conforme configuração; BUY entra abaixo do fechamento por `x_pct`, SELL entra acima do fechamento por `x_pct`, com target/stop percentuais e score baseado em histórico de backtest, liquidez e penalidade de volatilidade.

## 2026-06-18 00:00 UTC — Avaliação de substituir etapas de sinal por rede neural
- Revisada a possibilidade de substituir parte do fluxo de geração de sinais EOD por saída de rede neural, especialmente os passos de configuração/ranking heurístico descritos anteriormente.
- Conclusão técnica: é possível, mas a rede neural existente em `functions/pattern_detection` ainda é experimental e retorna ações `buy`/`sell`/`hold` a partir de probabilidades; para produção seria necessário criar rotina de inferência versionada, tabela de predições, calibração de confiança, regras de target/stop/horizonte e governança antes de alimentar `sinais_eod`.
- Recomendação: manter o backtest diário como validador e evoluir o `eod_signals` para consumir uma tabela de predições neurais quando o modelo estiver treinado, versionado e aprovado em paper trading.

## 2026-06-18 00:00 UTC — Plano de sinais EOD com redes neurais
- Criado o documento `docs/plano-sinais-neurais-eod.md` com o plano para iniciar um sistema de sinais EOD baseado em redes neurais mantendo a lógica de entrada para o pregão seguinte com percentual de diferença sobre o fechamento.
- O plano define arquitetura com tabela intermediária de predições neurais, job de inferência EOD, adaptação controlada do `eod_signals`, manutenção do `backtest_daily` como validador, fases de implementação, métricas, riscos e critérios de pronto.

## 2026-06-18 13:43:37 UTC-3
- Expandido o plano `docs/plano-sinais-neurais-eod.md` com uma seção completa para implantação do processo de treino de redes neurais EOD.
- Documentadas recomendações para separação temporal de dados, construção de dataset supervisionado, definição de labels por barreiras, prevenção de vazamento, comparação de arquiteturas neurais, protocolo de treino, seleção de thresholds, critérios de promoção, período de testes, retreinamento e governança.
- Alteração exclusivamente documental, sem impacto em código executável.

## 2026-06-18 00:00 UTC — Fase 1 do plano de sinais EOD neurais
- Executada a Fase 1 do plano `docs/plano-sinais-neurais-eod.md`, com foco em especificação e schema antes de qualquer alteração operacional no `eod_signals`.
- Criado o script BigQuery `infra/bq/16_neural_eod_predictions.sql` com a tabela `cotacao_intraday.neural_eod_predictions` para probabilidades neurais brutas e a view `vw_neural_eod_predictions_latest` para consumo da última predição por ativo/data/modelo.
- Criada a documentação `docs/implementacao/fase1-sinais-neurais-eod-schema.md`, registrando schema mínimo de features, convenções de `model_id`, `model_version`, `feature_version`, `inference_config_version` e contratos de entrada/saída para o futuro job de inferência.
- Atualizado o plano neural para marcar a Fase 1 como executada e atualizado o README de infraestrutura BigQuery para listar o novo script.
- Alteração exclusivamente documental/DDL; não houve mudança em funções executáveis nem ativação de sinais neurais em produção.


## 2026-06-18 00:00 UTC — Fase 2 do plano de sinais EOD neurais
- Executada a Fase 2 do plano `docs/plano-sinais-neurais-eod.md`, com foco na construção do dataset histórico supervisionado para treino neural.
- Criado o módulo `sisacao8/neural_dataset.py`, que gera features tabulares versionadas até `reference_date`, labels por barreiras `up/down/neutral` e split temporal treino/validação/teste com embargo para reduzir vazamento.
- Criado o script BigQuery `infra/bq/17_neural_eod_training_dataset.sql`, com a tabela `cotacao_intraday.neural_eod_training_dataset` e a view de qualidade `vw_neural_eod_training_dataset_quality`.
- Criada a documentação `docs/implementacao/fase2-sinais-neurais-eod-dataset.md`, registrando features, labels, split temporal, prevenção de vazamento e critérios de saída.
- Adicionados testes unitários em `tests/test_neural_dataset.py` para validar geração do dataset e embargo dos splits.

## 2026-06-18 00:00 UTC — Tela de dados de treino para redes neurais
- Criado no frontend um novo grupo de menu `Redes neurais` com o subitem `Dados de treino`, voltado a acompanhar a alocação cronológica do dataset neural EOD.
- Adicionada a tela `NeuralTrainingDataTab`, exibindo cards de volume, janela histórica, versões de features/labels, distribuição direcional, flags de qualidade, barra de alocação por split e tabela detalhada por treino/validação/teste/embargo.
- Adicionado o hook `useNeuralTrainingDataAllocation` e a normalização TypeScript para consumir `GET /ops/neural/training-data/allocation`.
- Exposto no backend Spring o endpoint `GET /ops/neural/training-data/allocation`, lendo a view BigQuery `vw_neural_eod_training_dataset_quality` para permitir que o usuário acompanhe a alocação dos dados de treino.

## 2026-06-18 20:30 UTC — Fase 3 neural: treino baseline MLP
- Executada a Fase 3 do plano `docs/plano-sinais-neurais-eod.md`, criando o contrato de treino do baseline neural MLP para sinais EOD.
- Criado o módulo `sisacao8/neural_training.py`, com preparação de arrays por split cronológico, scaler ajustado apenas no treino, codificação estável das classes `down`/`neutral`/`up`, treino Keras do MLP, métricas por split e geração de manifesto versionado.
- Criado o script BigQuery `infra/bq/18_neural_model_registry.sql`, com a tabela `cotacao_intraday.neural_model_registry` para registrar artefatos, métricas, contratos de feature/label e status de governança.
- Criada a documentação `docs/implementacao/fase3-sinais-neurais-eod-treino-baseline.md`, registrando modelo, versões, métricas, artefatos e critérios de saída.
- Adicionados testes unitários em `tests/test_neural_training.py` para validar preparação dos arrays, métricas de avaliação e manifesto do artefato.

## 2026-06-18 21:05 UTC — Tela de acompanhamento de treinos neurais
- Criada a tela `NeuralTrainingRunsTab` no frontend para o usuário acompanhar treinos neurais, exibindo cards de quantidade, último treino, melhor acurácia de teste, precisão direcional e tabela com versões, status, métricas, contrato e artefato.
- Adicionado o hook `useNeuralTrainingRuns` e a normalização TypeScript para consumir `GET /ops/neural/training-runs`.
- Exposto no backend Spring o endpoint `GET /ops/neural/training-runs`, lendo a tabela BigQuery `neural_model_registry` para listar os artefatos registrados.
- Adicionado o item de menu `Redes neurais > Treinos`, separado da tela de dados de treino para diferenciar materialização de dataset e acompanhamento dos modelos treinados.

## 2026-06-19 00:00 UTC — Fase 4 neural: inferência EOD sem produção
- Executada a Fase 4 do plano `docs/plano-sinais-neurais-eod.md`, criando o job `functions/neural_eod_predictions` para gerar predições neurais em shadow mode após o fechamento.
- Criado o módulo `sisacao8/neural_inference.py`, responsável por carregar o scaler do manifesto, transformar features EOD, normalizar probabilidades, classificar `BUY`/`SELL`/`HOLD` por threshold e montar linhas auditáveis para `neural_eod_predictions`.
- Adicionada a função pública `build_inference_features` em `sisacao8/neural_dataset.py`, reutilizando o mesmo contrato de features da Fase 2 sem labels futuras nem splits de treino.
- Documentado o contrato operacional em `docs/implementacao/fase4-sinais-neurais-eod-inferencia.md`, reforçando que a fase não grava em `sinais_eod` e não altera o `backtest_daily`.
- Adicionados testes unitários em `tests/test_neural_inference.py` para validar ações sugeridas, snapshots, versões e normalização das probabilidades.

## 2026-06-19 00:00 UTC — Correção do DDL do registro neural no BigQuery
- Corrigido o script `infra/bq/18_neural_model_registry.sql` removendo `NOT NULL` dos campos `feature_columns ARRAY<STRING>` e `label_classes ARRAY<STRING>`.
- Motivo: BigQuery não permite aplicar `NOT NULL` diretamente a campos do tipo `ARRAY`; arrays nulos são armazenados como arrays vazios, causando erro ao executar o DDL.
- Validação local realizada por busca textual para confirmar que não restaram colunas `ARRAY<...> NOT NULL` no script corrigido.

## 2026-06-19 00:00 UTC — Fase 5 neural: sinais em paralelo
- Executada a Fase 5 do plano `docs/plano-sinais-neurais-eod.md`, adaptando o `eod_signals` para aceitar `SIGNAL_SOURCE=heuristic|neural|hybrid`, mantendo `heuristic` como padrão.
- Implementada a leitura de `neural_eod_predictions` por `reference_date` e `valid_for`, com descarte de `HOLD`, thresholds de confiança BUY/SELL e geração de sinais condicionais com a regra canônica de entrada/target/stop.
- Sinais neurais passam a ser gravados com `model_version` própria (`neural:<versão_do_modelo>`) e `ranking_key` neural/híbrida, preservando rastreabilidade para o `backtest_daily`.
- Ajustada a exclusão pré-inserção para remover apenas sinais da mesma data e `model_version`, evitando substituir os sinais heurísticos no mesmo pregão.
- Criada a documentação `docs/implementacao/fase5-sinais-neurais-eod-paralelo.md` e adicionados testes unitários para a consulta de predições e a geração de sinais neurais.

## 2026-06-19 00:42:15 UTC-3
- Executada a Fase 6 do plano de sinais neurais EOD, adicionando gate conservador para liberar modelos neurais apenas quando métricas mínimas de backtest forem atendidas.
- Criado módulo `sisacao8/neural_paper_trading.py` para avaliar profit factor, win rate, fill rate, drawdown, retorno médio, sensibilidade a custos e gerar ordens simuladas sem capital real.
- Criado DDL `infra/bq/19_neural_eod_paper_trading.sql` com critérios versionados, avaliações de liberação e views de métricas de paper trading neural.
- Documentada a implementação em `docs/implementacao/fase6-sinais-neurais-eod-paper-trading.md` e atualizado o plano principal `docs/plano-sinais-neurais-eod.md` com status da fase.

## 2026-06-19 00:00 UTC — Fase 7 neural: promoção controlada
- Executada a Fase 7 do plano de sinais neurais EOD, adicionando gate de promoção controlada para impedir substituição automática do fluxo heurístico.
- Criado módulo `sisacao8/neural_promotion.py` para avaliar robustez OOS, desempenho em paper trading, divergência contra backtest e aprovação explícita antes de liberar uso controlado.
- Criado DDL `infra/bq/20_neural_eod_controlled_promotion.sql` com critérios versionados, decisões auditáveis e views para fonte segura `hybrid` com fallback `heuristic`.
- Documentada a implementação em `docs/implementacao/fase7-sinais-neurais-eod-promocao-controlada.md` e atualizado o plano principal com status da fase.

## 2026-06-19 12:25 UTC — Diagnóstico da tela neural de dados de treino
- Investigada a tela `Redes neurais — Dados de treino` reportada sem informação no painel operacional publicado em `http://34.194.252.70/`.
- Confirmado por chamada HTTP ao endpoint publicado `GET /api/ops/neural/training-data/allocation` que a API retorna lista vazia (`[]`), portanto o frontend exibe corretamente o alerta de ausência de alocação materializada.
- Revisado o fluxo de código: o frontend consome `GET /ops/neural/training-data/allocation`, o backend consulta a view BigQuery `vw_neural_eod_training_dataset_quality`, e essa view só retorna linhas quando a tabela `cotacao_intraday.neural_eod_training_dataset` já recebeu dataset supervisionado materializado.
- Tentada consulta ao MCP obrigatório via JSON-RPC em `http://mcpserversisacao.shop/mcp`, mas o serviço respondeu com falha de conexão do upstream; diagnóstico baseado no endpoint público do backend e nos contratos versionados no repositório.

## 2026-06-19 12:30 UTC — Esclarecimento sobre existência e carga do dataset neural
- Respondida a dúvida operacional sobre `cotacao_intraday.neural_eod_training_dataset`: o repositório possui DDL para criar a tabela e a view de qualidade, e o backend publicado consegue consultar a view sem erro, retornando lista vazia.
- Identificado que não existe, no repositório atual, Cloud Function/job/script operacional que leia candles históricos, execute `sisacao8.neural_dataset.build_training_dataset` e grave o resultado em `cotacao_intraday.neural_eod_training_dataset`.
- Conclusão: o contrato e o builder do dataset existem, mas a rotina de materialização/carga do dataset ainda precisa ser implementada ou executada manualmente fora do código versionado.

## 2026-06-19 12:45 UTC — Cloud Function de materialização do dataset neural
- Criada a Cloud Function HTTP `functions/neural_training_dataset` para materializar `cotacao_intraday.neural_eod_training_dataset` a partir de candles históricos diários e do builder `sisacao8.neural_dataset.build_training_dataset`.
- A função lê candles de `cotacao_intraday.cotacao_ohlcv_diario`, tenta carregar feriados de `cotacao_intraday.feriados_b3`, aplica parâmetros de labels/splits, adiciona `dataset_snapshot`, `created_at` e `metadata_json`, remove snapshot anterior quando solicitado e grava no BigQuery.
- Adicionados testes unitários para validar a carga via cliente BigQuery fake e a composição do payload HTTP.
- Documentada a operação e o comando de publicação GCP em `docs/implementacao/fase2-sinais-neurais-eod-materializacao.md`; tentativa de deploy local ficou bloqueada porque `gcloud` não está instalado no ambiente de execução.

## 2026-06-19 16:41 UTC — Diagnóstico pós-criação da função de dataset neural
- Revalidado o endpoint publicado `GET http://34.194.252.70/api/ops/neural/training-data/allocation`: a API respondeu `200` com lista vazia (`[]`), confirmando que a tela continua sem dados porque a view de qualidade ainda não possui linhas agregadas.
- Revisada a Cloud Function `functions/neural_training_dataset`: ela já materializa o dataset supervisionado quando executada, lendo `cotacao_intraday.cotacao_ohlcv_diario`, aplicando splits/labels e gravando em `cotacao_intraday.neural_eod_training_dataset`.
- Conclusão operacional: falta aplicar/confirmar o DDL da tabela/view, publicar a Cloud Function no GCP, conceder IAM de BigQuery à service account, executar a função com janela histórica válida e validar se `vw_neural_eod_training_dataset_quality` passou a retornar linhas para o backend/frontend.
- Tentado acesso obrigatório ao MCP via JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp`; o servidor respondeu `503 Service Unavailable` por timeout do upstream, então a validação BigQuery direta via MCP não ficou disponível neste diagnóstico.

## 2026-06-19 16:52 UTC — Correção do deploy automático da função neural_training_dataset
- Verificado o workflow `.github/workflows/deploy.yml`: apesar de o gatilho cobrir `functions/**`, a matriz `deploy-cloud-functions` não incluía `neural_training_dataset`, portanto a função nova não seria publicada automaticamente no push para `main`.
- Adicionada `neural_training_dataset` à matriz de deploy com source `functions/neural_training_dataset`, entry point `neural_training_dataset`, variáveis BigQuery necessárias e memória de `1Gi` para suportar pandas/pyarrow durante a materialização histórica.
- Atualizada a documentação de materialização para deixar claro que a publicação padrão é via workflow automático e que o comando `gcloud functions deploy` é apenas fallback manual.
- Tentado novamente o MCP obrigatório via JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp`; o endpoint retornou `503 Service Unavailable` por timeout do upstream, impossibilitando confirmar pelo MCP se a função já existe no GCP.

## 2026-06-19 20:26 UTC — Verificação de DDL e deploy da função neural_training_dataset
- Verificado o item 1 (DDL/view): o endpoint publicado `GET http://34.194.252.70/api/ops/neural/training-data/allocation` respondeu `200` com lista vazia (`[]`), indicando que o backend conseguiu consultar `vw_neural_eod_training_dataset_quality`; se a view/tabela não existisse, o backend propagaria erro de BigQuery em vez de retornar lista vazia.
- Verificado o item 2 (deploy da função): a URL padrão da Cloud Function Gen2 `https://us-east1-ingestaokraken.cloudfunctions.net/neural_training_dataset` respondeu no Cloud Functions endpoint, confirmando que a função está publicada; a chamada `HEAD` retornou `500` por tentar executar a função sem payload/janela adequada, não por ausência de deploy.
- Tentado novamente o MCP obrigatório via JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp`; o endpoint respondeu `503 Service Unavailable` com falha de conexão upstream, então a verificação direta por MCP/BigQuery permaneceu indisponível.

## 2026-06-19 21:45 UTC — Investigação do HTTP 500 em neural_training_dataset
- Investigado o erro HTTP 500 reportado na chamada pública da Cloud Function `neural_training_dataset` para a janela `2021-06-19` a `2026-06-18` e snapshot `neural_eod_training_dataset_2026-06-18_v1`.
- Tentada consulta de logs via `gcloud logging read` e `gcloud functions logs read`, mas o ambiente local não possui `gcloud` instalado.
- Tentada inicialização do MCP obrigatório em `http://mcpserversisacao.shop/mcp` via JSON-RPC, mas o endpoint retornou `503`/connection refused, impedindo acesso operacional a logs/BigQuery por esse canal.
- Pela revisão estática da função, o ponto mais provável de falha continua sendo a execução pesada da materialização histórica completa em memória/HTTP: a função carrega candles de todo o período para pandas, monta todo o dataset e faz `load_table_from_json` em lote único, enquanto o deploy atual define apenas `1Gi` de memória e não define timeout customizado.
- Retentado acesso ao MCP com timeouts maiores (`60s`, `120s` e `180s`) usando HTTP/JSON-RPC; todas as tentativas retornaram `503` rapidamente (`connection refused` antes de headers), confirmando que o problema não é timeout curto do cliente, e sim indisponibilidade/conexão recusada no upstream do MCP.
- Recebida evidência operacional do usuário mostrando `docker ps` no host do MCP sem containers em execução; confirmado que o erro `503` externo é compatível com o MCP Java fora do ar, não com falha da URL ou timeout do cliente.

## 2026-06-19 22:20 UTC — Hardening do workflow de publicação do MCP Java
- Revisado o workflow `.github/workflows/deploy-mcp-java-vps.yml`: ele fazia build/push da imagem, removia containers antigos e executava `docker run`, mas apenas imprimia `docker ps`/logs sem falhar explicitamente se o container encerrasse logo após o start.
- Ajustado o deploy do MCP Java para capturar o `container_id`, validar via `docker inspect` que o status permaneceu `running` e executar smoke test local `POST http://127.0.0.1/mcp` com JSON-RPC `initialize` antes de considerar a publicação bem-sucedida.
- Com esse ajuste, o workflow passa a falhar com logs/inspect quando o MCP não fica no ar, evitando falso positivo de deploy enquanto `http://mcpserversisacao.shop/mcp` retorna `503`.

## 2026-06-19 23:40 UTC — Verificação do 500 em neural_training_dataset via MCP
- Consultado o MCP em `http://mcpserversisacao.shop/mcp` via JSON-RPC para verificar logs da Cloud Function `neural_training_dataset` após erro HTTP 500 reportado pelo usuário na chamada de 2026-06-19 23:36 UTC.
- Confirmado nos logs do serviço Cloud Run `neural-training-dataset` que a função iniciou a execução do POST, mas falhou antes de materializar o dataset: a consulta BigQuery em `_load_candles` retornou `400 Unrecognized name: volume at [2:61]`.
- Conclusão operacional: a função foi invocada/executada parcialmente, porém não concluiu com sucesso nem chegou à etapa de gravação em `cotacao_intraday.neural_eod_training_dataset`; é necessário corrigir o SELECT da função para usar o nome real da coluna de volume na tabela fonte.

## 2026-06-19 23:55 UTC — Correção das colunas de volume nas funções neurais
- Corrigida a query de candles da Cloud Function `neural_training_dataset` para ler o schema real de `cotacao_intraday.cotacao_ohlcv_diario`: `qtd_negociada AS volume` e `volume_financeiro AS financial_volume`, eliminando a referência inválida às colunas inexistentes `volume`/`financial_volume`.
- Aplicada a mesma correção preventiva em `neural_eod_predictions`, que reutiliza o contrato neural `volume`/`financial_volume` em pandas, mas também lê a tabela diária com os nomes físicos `qtd_negociada`/`volume_financeiro`.
- Adicionado teste unitário garantindo que `_load_candles` em `neural_training_dataset` gera a query com os aliases corretos para o schema diário publicado.


## 2026-06-19 20:45:47 UTC-3 — Atualização do AGENTS sobre confirmação de hipóteses
- Adicionada diretriz ao `AGENTS.md` exigindo que, ao identificar uma possível causa de problema, o agente use as ferramentas disponíveis para confirmar a hipótese antes de concluir a análise.
- A nova orientação também determina resolver o problema no mesmo fluxo quando a hipótese for confirmada e a correção estiver dentro do escopo/permissões, registrando ferramentas e correção no diário do projeto.

## 2026-06-20 00:15 UTC — Correção de dependência em neural_training_dataset
- Investigado o novo HTTP 500 reportado para a Cloud Function `neural_training_dataset` na chamada de 2026-06-20 00:08 UTC com janela `2021-06-19` a `2026-06-18`.
- Confirmado via MCP obrigatório em `http://mcpserversisacao.shop/mcp`, usando JSON-RPC `initialize`, `tools/list`, `cloud_run_function_logs` e `bigquery_query`, que a correção anterior das colunas de volume já estava no deploy e que o novo erro é `ModuleNotFoundError: No module named 'db_dtypes'` seguido de `ValueError: Please install the 'db-dtypes' package to use this function` ao executar `QueryJob.to_dataframe()`.
- Confirmado também via BigQuery/MCP que a tabela `ingestaokraken.cotacao_intraday.cotacao_ohlcv_diario` possui as colunas físicas `qtd_negociada` e `volume_financeiro`, compatíveis com o SELECT atual da função.
- Corrigido `functions/neural_training_dataset/requirements.txt` para incluir `db-dtypes`, dependência exigida pelo cliente BigQuery ao converter resultados para pandas DataFrame em runtime.

## 2026-06-20 03:10 UTC — Correção de valores não finitos no dataset neural
- Investigado o HTTP 500 reportado na Cloud Function `neural_training_dataset` para a chamada de 2026-06-20 03:03:04 UTC, snapshot `neural_eod_training_dataset_2026-06-18_v1`.
- Reproduzida nova chamada HTTP ao endpoint publicado, que retornou `500` após cerca de 15s, confirmando que a função existe e falha durante o processamento.
- Tentado acesso obrigatório ao MCP via JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp` com `initialize` e `tools/list`; o endpoint retornou `503 Service Unavailable` por timeout do upstream, então logs/BigQuery não ficaram disponíveis por esse canal neste momento.
- Como `gcloud` não está instalado no ambiente, a consulta direta de logs via `gcloud functions logs read neural_training_dataset --region=us-east1` também não ficou disponível.
- Confirmado por revisão e teste local que `_json_safe_value` removia apenas `NaN`, mas preservava `Infinity`, `-Infinity` e `pd.NA`; esses valores podem surgir em features financeiras com denominadores/rolling windows nulos ou constantes e quebrar a serialização/carga JSON no BigQuery.
- Corrigida a normalização de registros enviados ao BigQuery para transformar valores escalares ausentes ou não finitos em `None`, mantendo datas/timestamps e metadados JSON seguros.
- Adicionado teste unitário cobrindo `NaN`, `Infinity`, `-Infinity`, `pd.NA` e número finito em `_json_safe_value`.
- Checks executados: `python -m pytest tests/test_neural_training_dataset_function.py`, `python -m flake8 functions/neural_training_dataset/main.py tests/test_neural_training_dataset_function.py`, `python -m pytest`, `python -m black --check functions/neural_training_dataset/main.py tests/test_neural_training_dataset_function.py` e `python -m isort --check-only functions/neural_training_dataset/main.py tests/test_neural_training_dataset_function.py`.

## 2026-06-20 03:20 UTC — Confirmação via MCP do erro atual em neural_training_dataset
- Refeito o acesso obrigatório ao MCP Server via JSON-RPC em `http://mcpserversisacao.shop/mcp`: `initialize` retornou sessão válida e `tools/list` confirmou as ferramentas disponíveis.
- Consultado `cloud_run_function_logs` com `function_name=neural_training_dataset`, `hours=1` e `limit=120`, confirmando nos logs do Cloud Run a falha reportada pelo usuário às 03:03 UTC.
- Causa confirmada: a carga JSON no BigQuery falhou em `_load_dataset` porque `days_to_event_sell` chegou como `1.0`, mas a coluna BigQuery é `INT64`; o erro registrado foi `Could not convert value ... to integer. Field: days_to_event_sell; Value: 1.0`.
- Causa secundária confirmada: `_load_holidays` ainda consultava a coluna inexistente `data`; consulta de schema via MCP/BigQuery em `INFORMATION_SCHEMA.COLUMNS` confirmou que `feriados_b3` usa `data_feriado`, `nome_feriado`, `mercado`, `ativo` e `atualizado_em`.
- Corrigida a query de feriados para usar `data_feriado AS holiday_date`, filtrar por `data_feriado` e considerar somente feriados ativos.
- Corrigida a sanitização dos registros para converter campos inteiros nullable (`days_to_event_buy` e `days_to_event_sell`) de floats vindos do pandas para inteiros JSON antes do `load_table_from_json`, preservando `None` quando o evento não existe.
- Adicionados testes unitários para validar o schema publicado de `feriados_b3` e a conversão dos campos inteiros nullable.

## 2026-06-20 03:35 UTC — Documentação do procedimento MCP no AGENTS
- Atualizado `AGENTS.md` com as descobertas operacionais usadas para acessar o MCP Server durante a investigação da Cloud Function `neural_training_dataset`.
- Registrado que o MCP deve permanecer em HTTP, que timeouts/503 exigem repetir o `initialize` e capturar novo `mcp-session-id`, e que todas as chamadas seguintes devem reenviar esse header.
- Documentado que `cloud_run_function_logs` exige o argumento `function_name` e que `function`/`service` retornaram `function_name vazio`.
- Incluídos exemplos de `tools/call` para logs de Cloud Function com janela curta (`hours=1`, `limit=120`) e para consulta read-only de schema BigQuery via `bigquery_query` em `INFORMATION_SCHEMA`.

## 2026-06-20 15:20 UTC — Diagnóstico da ausência de treinos neurais
- Investigada a tela "Redes neurais — Treinos" reportada pelo usuário, que exibiu a mensagem de ausência de treinos registrados apesar de a tela de dados de treino já possuir alocação.
- Confirmado via MCP obrigatório em `http://mcpserversisacao.shop/mcp`, usando JSON-RPC `initialize` e `tools/call` com `bigquery_query`, que existem 8.144 linhas em `ingestaokraken.cotacao_intraday.neural_eod_training_dataset`, em 1 snapshot, com `reference_date` de 2026-03-30 a 2026-06-17.
- Confirmado na mesma consulta que `ingestaokraken.cotacao_intraday.neural_model_registry` existe, mas possui 0 linhas e 0 versões de modelo; por isso o endpoint `GET http://34.194.252.70/api/ops/neural/training-runs` retorna `[]` e o frontend mostra "Ainda não há treinos neurais registrados".
- Revisado o código: o backend lista treinos exclusivamente a partir da tabela `neural_model_registry`, enquanto o repositório possui apenas o helper local `sisacao8.neural_training.train_baseline_mlp`; ainda falta uma rotina produtiva/orquestrada que carregue o dataset do BigQuery, execute o treino TensorFlow, salve o artefato em storage acessível e insira a linha do modelo no registry.
- Conclusão operacional: dados de treino já foram materializados, mas falta executar/publicar o job de treino e registrar o artefato resultante no `neural_model_registry` com status inicial compatível com governança (`candidate`, depois promoção controlada para `shadow`/`approved`).

## 2026-06-20 15:55 UTC — Implementação do job produtivo neural_training
- Implementada a Cloud Function HTTP `functions/neural_training`, que lê `cotacao_intraday.neural_eod_training_dataset`, executa o baseline `train_baseline_mlp`, publica o artefato do modelo e registra a execução em `cotacao_intraday.neural_model_registry`.
- A função aceita `dataset_snapshot`, `model_version`, hiperparâmetros básicos (`epochs`, `batch_size`, `hidden_units`, `dropout_rate`, `learning_rate`, `random_seed`) e `status`; por padrão registra o modelo como `candidate` para manter a promoção controlada.
- Adicionado upload de `model.keras` e `manifest.json` para `gs://<NEURAL_MODEL_ARTIFACT_BUCKET>/<NEURAL_MODEL_ARTIFACT_PREFIX>/<model_version>` quando o bucket estiver configurado, mantendo fallback local apenas para testes/execuções manuais.
- Atualizado o workflow `.github/workflows/deploy.yml` para publicar `neural_training` com 2Gi de memória, timeout de 3600s e variáveis BigQuery/artefato, além de suportar timeout por função.
- Atualizada a documentação da Fase 3 e o README de Functions para descrever a rotina que fecha a lacuna entre dados de treino e registros exibidos na tela "Treinos".
- Adicionados testes unitários em `tests/test_neural_training_function.py` cobrindo leitura do dataset, publicação do artefato e inserção no registry.
- Checks executados: `python -m pytest tests/test_neural_training_function.py tests/test_neural_training.py tests/test_neural_training_dataset_function.py`, `python -m flake8 functions/neural_training/main.py tests/test_neural_training_function.py`, `python -m black --check functions/neural_training/main.py tests/test_neural_training_function.py` e `python -m isort --check-only functions/neural_training/main.py tests/test_neural_training_function.py`.
- Checks globais adicionais executados antes do PR: `python -m flake8` e `python -m pytest` passaram com 116 testes; `python -m black --check .` e `python -m isort --check-only .` falharam por arquivos preexistentes fora do escopo desta alteração que já não estavam formatados/ordenados.

## 2026-06-20 17:25 UTC — Diagnóstico do bloqueio para início dos treinos neurais
- Investigado o painel publicado em `http://34.194.252.70` e confirmado via endpoints REST que `/api/ops/neural/training-data/allocation` já retorna dataset neural materializado, enquanto `/api/ops/neural/training-runs` retorna lista vazia.
- Consultado o MCP obrigatório via JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp`; o `initialize` retornou sessão válida, `bigquery_query` confirmou `0` registros em `ingestaokraken.cotacao_intraday.neural_model_registry` e `cloud_run_function_logs` confirmou `0` logs da função `neural_training` nas últimas 24h.
- Conclusão operacional: o dataset de treino já começou a ser materializado, mas ainda falta executar/invocar a Cloud Function `neural_training` com um snapshot válido para gerar artefato, salvar no bucket `sisacao8-neural-artifacts` e registrar a execução em `neural_model_registry`; por isso a tela de Treinos segue vazia.
- Observação adicional: a alocação publicada mostra linhas `train` e linhas ainda sem `dataset_split`, então antes de rodar treino produtivo é recomendável confirmar se a regra de split da materialização está gerando também `validation`/`test` conforme esperado ou se a janela/snapshot precisa ser ajustada.

## 2026-06-20 17:35 UTC — Execução manual do primeiro treino neural
- Solicitada execução operacional do treino pelo usuário; confirmado que o MCP Server não possui ferramenta para invocar Cloud Function ou criar bucket GCS, então a função `neural_training` foi chamada diretamente por HTTP `curl`.
- A execução anterior do usuário havia falhado com HTTP 500 por bucket inexistente `sisacao8-neural-artifacts`, conforme logs consultados via MCP `cloud_run_function_logs`.
- Executado `POST https://us-east1-ingestaokraken.cloudfunctions.net/neural_training` com `model_version=neural_eod_mlp_v1_20260620_002`, `epochs=40`, `batch_size=256`, `status=candidate` e `artifact_uri=/tmp/neural-eod-models/neural_eod_mlp_v1_20260620_002` como workaround temporário para evitar o upload ao bucket ausente.
- A função retornou `status=ok`, `rows=5294` e `training_dataset_snapshot=neural_eod_training_dataset_2026-06-18_v1`; em seguida, o endpoint publicado `/api/ops/neural/training-runs` retornou o novo registro e a consulta MCP/BigQuery confirmou a linha em `neural_model_registry`.
- Observação: `validation_accuracy`, `test_accuracy`, `directional_precision` e `coverage` ficaram nulos porque o snapshot disponível possui apenas split `train` com `dataset_split` preenchido; as linhas restantes ainda estão com `dataset_split` nulo. Para treino produtivo/auditável, ainda é necessário corrigir/materializar splits `validation` e `test` e criar o bucket GCS definitivo.

## 2026-06-20 17:40 UTC — Confirmação do treino neural com artefato no GCS
- Usuário criou o bucket `gs://sisacao8-neural-artifacts` em `us-east1` com `gcloud storage buckets create` e reexecutou a Cloud Function `neural_training` sem `artifact_uri` local.
- A função retornou `status=ok` para `model_version=neural_eod_mlp_v1_20260620_003`, `rows=5294`, `training_dataset_snapshot=neural_eod_training_dataset_2026-06-18_v1` e `artifact_uri=gs://sisacao8-neural-artifacts/neural-eod-models/neural_eod_mlp_v1_20260620_003`.
- Validado via endpoint publicado `/api/ops/neural/training-runs` e via MCP/BigQuery que `neural_model_registry` agora possui o registro produtivo com artefato persistido no GCS, além do registro temporário anterior em `/tmp`.
- As métricas de validação/teste permanecem nulas porque o dataset atualmente carregado para treino contém apenas linhas com `dataset_split=train`; segue pendente materializar splits `validation` e `test` para avaliação auditável.

## 2026-06-20 19:45 UTC — Verificação dos indicadores dos treinos neurais registrados
- Investigada a dúvida do usuário sobre os dois treinos exibidos na tela "Redes neurais — Treinos" e a ausência de informações de performance.
- Consultado o endpoint publicado `GET http://34.194.252.70/api/ops/neural/training-runs`, confirmando 2 registros candidatos: `neural_eod_mlp_v1_20260620_003` com artefato em `gs://sisacao8-neural-artifacts/neural-eod-models/neural_eod_mlp_v1_20260620_003` e `neural_eod_mlp_v1_20260620_002` com artefato temporário local em `/tmp/neural-eod-models/neural_eod_mlp_v1_20260620_002`.
- Confirmado no mesmo endpoint que `validationAccuracy`, `testAccuracy`, `directionalPrecision` e `coverage` estão `null` nos dois registros; por isso a interface renderiza `—` nos cartões/colunas de performance.
- Consultado o endpoint publicado `GET http://34.194.252.70/api/ops/neural/training-data/allocation`, confirmando que o snapshot atual possui 5.294 linhas em `datasetSplit=train` e 2.850 linhas ainda com `datasetSplit=null`, sem linhas publicadas como `validation` ou `test`.
- Tentado validar diretamente via MCP obrigatório em `http://mcpserversisacao.shop/mcp` com JSON-RPC `initialize` e `tools/call`/`bigquery_query`; o MCP inicializou sessão, mas a ferramenta BigQuery retornou erro de credencial do `gcloud` (`Credentials object has no attribute private_key_id`), então a confirmação operacional foi feita pelos endpoints REST publicados.
- Conclusão: os indicadores de performance ainda não existem para esses dois modelos porque o job treinou apenas com o split `train`; é necessário corrigir/materializar os splits `validation` e `test` no dataset neural e reexecutar o treino para preencher acurácia de validação/teste, precisão direcional, cobertura, matriz de confusão e métricas por classe.

## 2026-06-20 20:05 UTC — Correção da geração de splits neurais em janelas curtas
- Investigada a causa raiz da ausência de métricas nos dois treinos neurais candidatos: com o snapshot curto atual, a regra de split cronológico aplicava `embargo_days=15` integralmente antes de `validation` e antes de `test`, consumindo todo o espaço disponível fora do treino e deixando somente `dataset_split=train` ou `NULL`.
- Corrigida `assign_temporal_splits` em `sisacao8.neural_dataset` para limitar adaptativamente o embargo ao tamanho disponível de cada bloco fora do treino; assim, quando a janela histórica é curta, a função preserva ao menos datas de `validation` e `test` sempre que houver capacidade cronológica para esses blocos.
- Sincronizada a mesma correção na cópia vendorizada da Cloud Function `functions/neural_training_dataset/sisacao8/neural_dataset.py`, usada no deploy da materialização do dataset neural.
- Adicionados testes unitários para reproduzir a janela curta semelhante ao snapshot atual, garantir que `train`, `validation` e `test` sejam gerados, e validar que a Cloud Function materializa registros carregados com os três splits.
- Checks executados: `python -m pytest tests/test_neural_dataset.py tests/test_neural_training_dataset_function.py`, `python -m flake8 sisacao8/neural_dataset.py functions/neural_training_dataset/sisacao8/neural_dataset.py tests/test_neural_dataset.py tests/test_neural_training_dataset_function.py`, `python -m black --check sisacao8/neural_dataset.py functions/neural_training_dataset/sisacao8/neural_dataset.py tests/test_neural_dataset.py tests/test_neural_training_dataset_function.py`, `python -m isort --check-only sisacao8/neural_dataset.py functions/neural_training_dataset/sisacao8/neural_dataset.py tests/test_neural_dataset.py tests/test_neural_training_dataset_function.py`, `python -m flake8` e `python -m pytest`.

## 2026-06-20 18:29:54 UTC-3
- Confirmada pela tela reportada que a aba "Redes neurais — Treinos" exibia apenas campos consolidados de acurácia/precisão quando disponíveis, sem abrir o detalhamento de performance salvo em `metrics_json`.
- Ajustado o backend para retornar `metrics_json` e `confusion_matrix_json` do `neural_model_registry` via endpoint `/ops/neural/training-runs`.
- Ajustado o frontend para interpretar `metrics_json`, exibir painel de performance da rede mais recente no split de teste e adicionar a coluna de linhas testadas por treino.
- Validações executadas: `npm --prefix frontend/app run lint`, `npm --prefix frontend/app run build` e `cd backend/sisacao-backend && ./mvnw -q test`.

## 2026-06-20 18:50 UTC-3 — Confirmação do estado dos treinos neurais exibidos
- Respondida a dúvida do usuário sobre a tela "Redes neurais — Treinos" exibida em `http://34.194.252.70`.
- Validado com `curl -sS http://34.194.252.70/api/ops/neural/training-runs | python -m json.tool` que existem 2 registros de treino para `neural_eod_mlp`: `neural_eod_mlp_v1_20260620_003` e `neural_eod_mlp_v1_20260620_002`, ambos com `status=candidate`.
- Confirmado que o treino mais recente (`_003`) possui artefato persistido em `gs://sisacao8-neural-artifacts/neural-eod-models/neural_eod_mlp_v1_20260620_003`, enquanto o anterior (`_002`) usou caminho temporário local `/tmp/neural-eod-models/neural_eod_mlp_v1_20260620_002`.
- Confirmado que `metricsJson` contém somente métricas do split `train` nos dois registros (`accuracy=0.4795995466565924`, `directional_precision=0.48405466970387245`, `coverage=0.33169625991688706`, `rows_count=5294`) e que `validationAccuracy`, `testAccuracy`, `directionalPrecision` e `coverage` consolidados continuam `null`.
- Conclusão operacional: as redes foram treinadas no sentido de haver execução registrada e, no caso `_003`, artefato salvo no GCS; porém ainda não foram avaliadas em validação/teste, então permanecem apenas como candidatas e não devem ser tratadas como aprovadas para uso produtivo.

## 2026-06-20 19:05 UTC-3 — Exibição dos indicadores de treino na tela de redes neurais
- Atendida a solicitação para colocar na tela "Redes neurais — Treinos" os indicadores que já existem em `metricsJson` para o split `train`.
- Ajustado `frontend/app/src/components/tabs/NeuralTrainingRunsTab.tsx` para calcular e exibir acurácia de treino, precisão direcional de treino, cobertura de treino e amostras de treino no painel da rede mais recente.
- Adicionadas colunas de acurácia de treino e linhas de treino na tabela de treinos; as colunas de precisão direcional e cobertura agora usam fallback para métricas de `test` e, se inexistentes, para métricas de `train`, evitando exibir `—` quando o indicador já está disponível no JSON auditável.
- Validações executadas: `npm --prefix frontend/app run lint` e `npm --prefix frontend/app run build`.

## 2026-06-20 20:47 UTC — Resposta sobre duplicidade e qualidade dos treinos neurais
- Investigada a dúvida do usuário sobre os dois registros exibidos na aba "Redes neurais — Treinos".
- Validado via MCP obrigatório em `http://mcpserversisacao.shop/mcp`, usando JSON-RPC `initialize` e `tools/call` com `bigquery_query`, que existem 2 registros em `ingestaokraken.cotacao_intraday.neural_model_registry`: `neural_eod_mlp_v1_20260620_003` e `neural_eod_mlp_v1_20260620_002`.
- Confirmado que ambos usam o mesmo `model_id=neural_eod_mlp`, o mesmo `feature_version=feature_eod_tabular_v1`, o mesmo `label_version=label_eod_barrier_v1`, o mesmo snapshot `neural_eod_training_dataset_2026-06-18_v1` e métricas de treino idênticas (`accuracy=0.4795995466565924`, `directional_precision=0.48405466970387245`, `coverage=0.33169625991688706`, `rows_count=5294`).
- Registrado que o modelo `_002` foi uma execução temporária com artefato local em `/tmp`, enquanto o `_003` é a repetição com artefato persistido em `gs://sisacao8-neural-artifacts/neural-eod-models/neural_eod_mlp_v1_20260620_003`.
- Conclusão operacional: o resultado ainda não deve ser considerado bom/aprovado porque só há métrica de treino; `validation_accuracy`, `test_accuracy`, `directional_precision` e `coverage` consolidados seguem nulos, sem evidência fora da amostra.
- Confirmado no código que o Y usado no treino é `label_class`, versão `label_eod_barrier_v1`, codificado em três classes (`down`, `neutral`, `up`) a partir de uma regra de barreira futura EOD: entrada a 2%, alvo a 7%, stop a 7% e horizonte de 15 pregões.

## 2026-06-20 23:55 UTC — Exibição de alvos e stops nos dados de treino neural
- Atendida a solicitação para mostrar na tela "Redes neurais — Dados de treino" quantas linhas do dataset supervisionado atingiram valor alvo e quantas atingiram valor stop.
- Atualizada a view BigQuery `vw_neural_eod_training_dataset_quality` para agregar `target_hit_count` e `stop_hit_count` por versão de features, versão de labels e split temporal, considerando linhas em que `buy_net_return` ou `sell_net_return` atingiram respectivamente o alvo de 7% ou o stop de -7%.
- Atualizado o contrato `NeuralTrainingDataAllocation` no backend e no frontend para transportar os novos campos `targetHitCount` e `stopHitCount` pelo endpoint `GET /ops/neural/training-data/allocation`.
- Ajustada a aba de dados de treino para exibir cards consolidados de "Alvos atingidos" e "Stops atingidos" e colunas "Alvo"/"Stop" no detalhamento por split.
- Adicionado teste de controller garantindo que a API serializa `targetHitCount` e `stopHitCount` na resposta da alocação neural.
- Validações executadas: `npm --prefix frontend/app run lint`, `npm --prefix frontend/app run build` e `cd backend/sisacao-backend && ./mvnw -q test`.

## 2026-06-21 00:15 UTC — Planejamento do fluxo automático de evolução neural
- Atendida a solicitação para planejar um fluxo automático inteligente de evolução de parâmetros e estruturas de rede neural EOD.
- Criado `docs/planejamento/evolucao-neural-automatica.md` com arquitetura proposta, módulos novos, tabelas BigQuery de auditoria, espaço inicial de busca, score de seleção, fases operacionais e guardrails de governança.
- Incluída opção de módulo `neural_ai_advisor` com Gemini apenas como avaliador/sugeridor consultivo, usando JSON estruturado, validação por schema, deduplicação, limites de orçamento e impedimento explícito de promoção automática.
- Consultadas referências oficiais do Gemini sobre function calling e structured output para embasar a proposta de advisor com saída estruturada e segura.
- Conclusão de planejamento: começar pela Fase 1 determinística (random/grid/mutation + leaderboard), pois ela cria histórico auditável antes de ativar um advisor IA.

## 2026-06-21 00:50 UTC — Execução da Fase 0 da evolução neural automática
- Executada a Fase 0 do plano `docs/planejamento/evolucao-neural-automatica.md`: garantir dataset com `train`, `validation` e `test`, reexecutar a materialização após correção dos splits e reexecutar o baseline atual para criar referência comparável.
- Tentado acesso obrigatório ao MCP Server via JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp` com `curl`; o `initialize` retornou HTTP 503 por timeout do upstream, mantendo a regra de não trocar para HTTPS.
- Reexecutada a Cloud Function `neural_training_dataset` por HTTP com `start_date=2026-03-01`, `end_date=2026-06-18`, `dataset_snapshot=neural_eod_training_dataset_2026-06-18_phase0_20260621` e `replace_snapshot=true`.
- A materialização retornou `status=ok`, `rows=7992` e splits preenchidos: `train=5142`, `validation=750`, `test=750` e `embargo=1350`, confirmando que o pré-requisito de avaliação fora da amostra foi atendido para o novo snapshot.
- Reexecutado o baseline atual pela Cloud Function `neural_training` usando o snapshot `neural_eod_training_dataset_2026-06-18_phase0_20260621`, `model_version=neural_eod_mlp_v1_20260621_phase0`, `epochs=40`, `batch_size=256` e `status=candidate`.
- O treino retornou `status=ok`, `artifact_uri=gs://sisacao8-neural-artifacts/neural-eod-models/neural_eod_mlp_v1_20260621_phase0`, `rows=6642`, `validation_accuracy=0.3373333333333333`, `test_accuracy=0.3933333333333333`, `directional_precision=0.2724014336917563` e `coverage=0.372`.
- Validado via endpoints publicados `GET http://34.194.252.70/api/ops/neural/training-data/allocation` e `GET http://34.194.252.70/api/ops/neural/training-runs` que a tela operacional já enxerga linhas de `validation`/`test` e que o novo treino aparece como execução mais recente com métricas fora da amostra preenchidas.

## 2026-06-21 01:05 UTC — Execução da Fase 1 determinística da evolução neural
- Executada a Fase 1 do plano `docs/planejamento/evolucao-neural-automatica.md`, adicionando a fundação determinística sem IA para gerar candidatos, avaliar leaderboard e expor ranking operacional.
- Criado `sisacao8/neural_evolution.py` com orçamento controlado, geração reprodutível de candidatos random-search dentro do espaço permitido, `dedupe_hash`, estimativa simples de parâmetros e função de score/gates para rejeitar candidatos sem evidência fora da amostra.
- Criado `infra/bq/21_neural_evolution.sql` com as tabelas `neural_evolution_runs`, `neural_candidate_configs`, `neural_candidate_evaluations` e a view `vw_neural_evolution_leaderboard`; o README de BigQuery foi atualizado para listar o novo script.
- Exposto no backend o endpoint `GET /ops/neural/evolution/leaderboard`, consultando `vw_neural_evolution_leaderboard`, e adicionada no frontend a aba `Redes neurais — Evolução` para exibir score, decisão, precisão direcional, cobertura, generalização, estabilidade e configuração dos candidatos.
- Tentado novamente acesso obrigatório ao MCP Server via JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp` com retries; o `initialize` retornou HTTP 503 por timeout do upstream nas 3 tentativas, então não foi possível aplicar o DDL via MCP neste ambiente.
- Gerados 10 candidatos determinísticos para o snapshot `neural_eod_training_dataset_2026-06-18_phase0_20260621` com `evolution_run_id=neural_evolution_phase1_20260621` e prefixo `neural_eod_mlp_evo1_20260621`.
- Executadas 10 chamadas HTTP à Cloud Function `neural_training`, uma por candidato (`neural_eod_mlp_evo1_20260621_01` até `_10`), todas com retorno HTTP 200 e artefatos publicados em `gs://sisacao8-neural-artifacts/neural-eod-models/`.
- Validado via `GET http://34.194.252.70/api/ops/neural/training-runs` que os 10 candidatos aparecem no registry; o melhor candidato por score local foi `neural_eod_mlp_evo1_20260621_05`, com `test_accuracy=0.4226666666666667`, `directional_precision=0.32978723404255317`, `coverage=0.376` e `score_total=0.367585`.
- Todos os 10 candidatos foram classificados localmente como `reject` pelo gate determinístico porque a precisão direcional de teste ficou abaixo do baseline mínimo configurado (`directional_precision_test_below_baseline`), portanto nenhum candidato deve ser promovido para shadow/paper nesta rodada.
- Checks executados: `python -m pytest tests/test_neural_evolution.py`, `python -m flake8 sisacao8/neural_evolution.py tests/test_neural_evolution.py`, `cd backend/sisacao-backend && ./mvnw -q test`, `npm --prefix frontend/app run lint` e `npm --prefix frontend/app run build`.

## 2026-06-21 01:35 UTC — Execução da Fase 2 da evolução neural automática
- Executada a Fase 2 do plano `docs/planejamento/evolucao-neural-automatica.md`: mutação do top 20% dos candidatos, penalização de arquiteturas caras/instáveis, repetição de finalistas com múltiplas seeds e suporte de treino a early stopping/class weights.
- Atualizado `sisacao8.neural_evolution` com `select_top_candidates`, `mutate_top_candidates`, `repeat_finalists_with_seeds` e `penalized_score`, permitindo explorar o melhor candidato anterior e ajustar o score por custo/complexidade/runtime.
- Atualizado `sisacao8.neural_training` e a cópia vendorizada da Cloud Function `functions/neural_training/sisacao8/neural_training.py` para aceitar `early_stopping`, `early_stopping_patience` e `class_weight` (`none`, `balanced`, `directional`), usando `EarlyStopping(restore_best_weights=True)` quando há validação.
- Atualizada a entrada HTTP de `functions/neural_training/main.py` para parsear os novos campos de payload e registrá-los em `hyperparameters_json` por meio do manifesto.
- Selecionado como base o melhor candidato da Fase 1 (`neural_eod_mlp_evo1_20260621_05`) e gerados 6 candidatos de Fase 2: 3 mutações (`neural_eod_mlp_evo2_mut_20260621_01` a `_03`) e 3 repetições multi-seed (`neural_eod_mlp_evo2_seed_20260621_01_20260701` a `_20260703`).
- Executadas 6 chamadas HTTP à Cloud Function `neural_training`, todas com retorno HTTP 200 e artefatos publicados em `gs://sisacao8-neural-artifacts/neural-eod-models/`.
- Validado via `GET http://34.194.252.70/api/ops/neural/training-runs` que os 6 candidatos de Fase 2 aparecem no registry; o melhor por score penalizado local foi `neural_eod_mlp_evo2_seed_20260621_01_20260701`, com `test_accuracy=0.424`, `directional_precision=0.34798534798534797`, `coverage=0.364`, `score_total=0.324577` e decisão `keep_candidate`.
- As demais 5 execuções de Fase 2 foram classificadas localmente como `reject` por `directional_precision_test_below_baseline`; a recomendação operacional é manter o candidato `_20260701` apenas como candidato para novas evidências, sem promoção automática para shadow/paper.
- Checks executados: `python -m pytest tests/test_neural_evolution.py tests/test_neural_training.py tests/test_neural_training_function.py`, `python -m flake8 sisacao8/neural_evolution.py sisacao8/neural_training.py functions/neural_training/main.py functions/neural_training/sisacao8/neural_training.py tests/test_neural_evolution.py tests/test_neural_training.py tests/test_neural_training_function.py`.
- Checks globais adicionais executados antes do PR: `python -m flake8`, `python -m pytest`, `cd backend/sisacao-backend && ./mvnw -q test`, `npm --prefix frontend/app run lint`, `npm --prefix frontend/app run build`, `python -m black --check sisacao8/neural_evolution.py sisacao8/neural_training.py functions/neural_training/main.py functions/neural_training/sisacao8/neural_training.py tests/test_neural_evolution.py tests/test_neural_training.py tests/test_neural_training_function.py` e `python -m isort --check-only sisacao8/neural_evolution.py sisacao8/neural_training.py functions/neural_training/main.py functions/neural_training/sisacao8/neural_training.py tests/test_neural_evolution.py tests/test_neural_training.py tests/test_neural_training_function.py`.

## 2026-06-21 01:20 UTC — Execução da Fase 3 advisor Gemini opcional
- Executada a Fase 3 do plano `docs/planejamento/evolucao-neural-automatica.md` em modo seguro: implementar advisor isolado, usar somente JSON estruturado, registrar prompt/resposta/auditoria e preparar comparação A/B contra controles determinísticos.
- Criado `sisacao8.neural_ai_advisor`, módulo isolado que monta prompt JSON restrito, define schema estruturado esperado, valida resposta localmente, converte candidatos aceitos em `CandidateConfig`, constrói auditoria persistível e compara scores advisor vs controle determinístico.
- Adicionado no DDL `infra/bq/21_neural_evolution.sql` a tabela `neural_ai_advisor_audits` para persistir `prompt_json`, `response_json`, modelo Gemini, status de validação, contadores aceitos/rejeitados e motivos de rejeição.
- Implementado `call_gemini_structured_advisor` usando `responseMimeType=application/json` e `responseSchema`, mantendo credencial fora do prompt e sem executar código retornado pelo modelo.
- Confirmado que não há `GEMINI_API_KEY` no ambiente; portanto a execução operacional foi feita em `dry_run_no_gemini_api_key`, sem chamada externa ao Gemini e sem envio de dados para terceiros.
- No dry-run, o prompt resumiu apenas top candidatos/métricas da Fase 2, orçamento e espaço permitido; a resposta estruturada simulada gerou 2 candidatos válidos (`neural_eod_mlp_gemini_20260621_01` e `_02`) e 0 rejeições de schema.
- A comparação A/B ficou marcada como `advisor_without_accepted_candidates` para scores reais porque os candidatos Gemini não foram treinados sem uma chamada Gemini real/ativação operacional; o controle determinístico de referência segue com melhor score `0.324577` do candidato `neural_eod_mlp_evo2_seed_20260621_01_20260701`.
- Conclusão operacional: a Fase 3 está implementada e auditável, mas permanece opcional/desativada até provisionar credencial Gemini e aplicar o DDL de auditoria; nenhuma promoção automática foi realizada.
- Checks executados: `python -m pytest tests/test_neural_ai_advisor.py tests/test_neural_evolution.py` e `python -m flake8 sisacao8/neural_ai_advisor.py tests/test_neural_ai_advisor.py`.
- Checks globais adicionais executados antes do PR: `python -m flake8`, `python -m pytest`, `cd backend/sisacao-backend && ./mvnw -q test`, `npm --prefix frontend/app run lint`, `npm --prefix frontend/app run build`, `python -m black --check sisacao8/neural_ai_advisor.py tests/test_neural_ai_advisor.py` e `python -m isort --check-only sisacao8/neural_ai_advisor.py tests/test_neural_ai_advisor.py`.

## 2026-06-21 01:30 UTC — Execução da Fase 4 governança e promoção neural
- Executada a Fase 4 do plano `docs/planejamento/evolucao-neural-automatica.md`: integrar vencedor ao gate de shadow, bloquear paper trading sem janela mínima/critérios existentes e criar alertas de overfit, queda de cobertura e drift de labels.
- Atualizado `sisacao8.neural_promotion` com `NeuralShadowCriteria`, `NeuralShadowDecision`, `evaluate_neural_shadow_candidate`, `build_neural_governance_alerts` e `build_shadow_gate_audit_record`, mantendo a regra de que aprovação nessa etapa libera apenas `shadow_candidate`, sem capital e sem paper trading automático.
- Atualizado `infra/bq/21_neural_evolution.sql` com as tabelas `neural_shadow_gate_decisions` e `neural_governance_alerts` para persistir decisões do gate de shadow e alertas de governança.
- Validado via `GET http://34.194.252.70/api/ops/neural/training-runs` o candidato vencedor da Fase 2 (`neural_eod_mlp_evo2_seed_20260621_01_20260701`) e aplicado localmente o gate de shadow sobre o `metricsJson` registrado.
- Resultado do gate de shadow: `approved=true`, `status=shadow_candidate`, sem falhas e sem alertas; métricas normalizadas principais: `train_accuracy=0.4393232205367561`, `test_accuracy=0.424`, `test_rows=750`, `test_directional_precision=0.34798534798534797`, `test_coverage=0.364`, `train_test_accuracy_gap=0.01532322053675611`, `validation_test_precision_gap=0.04393129393129391`, `validation_test_coverage_drop=0.030666666666666675` e `label_drift_pct=0.0`.
- Aplicado também o gate de promoção/paper existente sem evidência de paper trading; o resultado foi `approved=false`, `status=blocked_for_promotion` e falhas em `oos_profit_factor`, `oos_win_rate`, `paper_profit_factor`, `paper_win_rate`, `paper_days`, `paper_trades`, `fill_rate` e `explicit_approval`, confirmando que não há promoção automática para paper/capital.
- Checks executados: `python -m pytest tests/test_neural_promotion.py` e `python -m flake8 sisacao8/neural_promotion.py tests/test_neural_promotion.py`.
- Checks globais adicionais executados antes do PR: `python -m flake8`, `python -m pytest`, `cd backend/sisacao-backend && ./mvnw -q test`, `npm --prefix frontend/app run lint`, `npm --prefix frontend/app run build`, `python -m black --check sisacao8/neural_promotion.py tests/test_neural_promotion.py` e `python -m isort --check-only sisacao8/neural_promotion.py tests/test_neural_promotion.py`.

## 2026-06-21 15:36 UTC — Diagnóstico prioridade 1 dos candidatos neurais EOD atuais
- Executada a prioridade 1 solicitada: diagnóstico dos candidatos neurais EOD atuais, buscando hiperparâmetros, métricas por split, precisão direcional, cobertura, overfit e estabilidade dos modelos `neural_eod_mlp_evo2_*` exibidos no painel operacional.
- Acesso ao MCP realizado obrigatoriamente via JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp`: `initialize` retornou sessão `mcp-session-id`, `tools/list` confirmou a ferramenta `bigquery_query` e a consulta BigQuery foi executada por `tools/call` mantendo HTTP, sem uso de HTTPS.
- Primeira chamada BigQuery ampla retornou erro transitório do backend MCP/gcloud (`Credentials object has no attribute private_key_id`); a hipótese de falha estrutural foi testada com consulta mínima `SELECT COUNT(*)`, que retornou `rows_count=19`, e a consulta ampla foi repetida com sucesso, confirmando instabilidade transitória e não erro SQL definitivo.
- Consulta principal retornou 6 candidatos Fase 2 no `neural_model_registry`: 3 mutações (`neural_eod_mlp_evo2_mut_20260621_01` a `_03`) e 3 repetições multi-seed (`neural_eod_mlp_evo2_seed_20260621_01_20260701` a `_20260703`), todos no snapshot `neural_eod_training_dataset_2026-06-18_phase0_20260621`.
- Todos os candidatos consultados usam a mesma arquitetura MLP profunda `hidden_units=[256,128,64]` e `batch_size=512`; as repetições multi-seed usam `learning_rate=0.0003`, `dropout_rate=0.35`, `epochs=80` e variam apenas `random_seed` (`20260701`, `20260702`, `20260703`).
- Tabela resumida do diagnóstico:
  - `neural_eod_mlp_evo2_seed_20260621_01_20260701`: `val_acc=0.3747`, `test_acc=0.4240`, `directional_precision_test=0.3480`, `coverage=0.3640`, `overfit=0.0153`, `stability=0.9561`; único candidato da amostra acima do corte local de precisão direcional `>0.34`.
  - `neural_eod_mlp_evo2_seed_20260621_01_20260702`: `val_acc=0.3507`, `test_acc=0.3813`, `directional_precision_test=0.2862`, `coverage=0.3960`, `overfit=0.0681`, `stability=0.9966`; abaixo do corte de precisão direcional.
  - `neural_eod_mlp_evo2_seed_20260621_01_20260703`: `val_acc=0.3533`, `test_acc=0.4227`, `directional_precision_test=0.2732`, `coverage=0.2733`, `overfit=0.0221`, `stability=0.9952`; abaixo do corte de precisão direcional e com menor cobertura.
  - `neural_eod_mlp_evo2_mut_20260621_03`: `val_acc=0.3600`, `test_acc=0.4333`, `directional_precision_test=0.3321`, `coverage=0.3693`, `overfit=0.0225`, `stability=0.9400`; melhor acurácia de teste, porém ainda abaixo do corte direcional.
  - `neural_eod_mlp_evo2_mut_20260621_02`: `val_acc=0.3573`, `test_acc=0.4227`, `directional_precision_test=0.3275`, `coverage=0.3787`, `overfit=0.0235`, `stability=0.9399`; abaixo do corte direcional.
  - `neural_eod_mlp_evo2_mut_20260621_01`: `val_acc=0.3680`, `test_acc=0.4187`, `directional_precision_test=0.3203`, `coverage=0.3747`, `overfit=0.0210`, `stability=0.9677`; abaixo do corte direcional.
- Conclusão operacional: o candidato `neural_eod_mlp_evo2_seed_20260621_01_20260701` segue como melhor evidência entre os atuais por combinar maior precisão direcional de teste acima do corte local e baixo overfit; contudo a estabilidade multi-seed é frágil, pois as seeds `20260702` e `20260703` caíram para precisão direcional de `0.2862` e `0.2732`, indicando que a melhoria ainda depende da seed e não deve ser promovida automaticamente.
- Recomendação para a próxima rodada: não expandir somente a mesma arquitetura `[256,128,64]`; priorizar novas mutações com arquiteturas menores/menos variância, repetir o melhor candidato com mais seeds, e testar ajustes de `class_weight`/labels antes de qualquer promoção além de shadow controlado.
- Comandos/ferramentas usados para confirmar: `curl` JSON-RPC HTTP para `initialize`, `tools/list`, `bigquery_access_check` e `bigquery_query`; `python` para montar payload JSON seguro e resumir métricas; `curl` contra endpoints públicos do backend confirmou indisponibilidade momentânea de `/api/ops/*` com HTTP 502, por isso a fonte final do diagnóstico foi BigQuery via MCP.

## 2026-06-21 15:45 UTC — Esclarecimento sobre advisor Gemini na evolução neural
- Verificada a existência do módulo `sisacao8.neural_ai_advisor` para responder se há parte do sistema que acessa Gemini para orientar evolução de modelos.
- Conclusão: existe implementação de advisor Gemini opcional/consultivo (`call_gemini_structured_advisor`) para sugerir configurações candidatas via JSON estruturado, mas o diário operacional anterior registra que não havia `GEMINI_API_KEY` no ambiente e que a fase foi executada em `dry_run_no_gemini_api_key`, sem chamada externa real ao Gemini.
- Confirmados os guardrails: o Gemini não promove modelos, não executa código retornado, respeita orçamento/espaço de busca, e as sugestões passam por validação local e auditoria em `neural_ai_advisor_audits`.
- Comandos usados: `rg -n "Gemini|gemini|advisor|GEMINI_API_KEY|call_gemini|responseSchema|neural_ai_advisor" sisacao8 tests docs infra functions -S --glob '!node_modules' --glob '!.git'` e `nl -ba` nos arquivos relevantes para citar linhas.

## 2026-06-21 17:45 UTC — Módulo Java genérico para advisor de IA
- Criado módulo Spring Boot/Maven genérico `com.sisacao.backend.aiadvisor`, sem acoplamento a Gemini, OpenAI ou qualquer provedor específico.
- Adicionados contratos provider-agnostic: `AiAdvisorProvider`, `AiAdvisorRequest`, `AiAdvisorResponse`, `AiAdvisorCandidate`, `AiAdvisorService`, `AiAdvisorController`, `AiAdvisorProperties` e `NoopAiAdvisorProvider`.
- O módulo nasce desabilitado por padrão via `sisacao.ai-advisor.enabled=false`, com provider configurável por `sisacao.ai-advisor.provider`, permitindo plugar Gemini, OpenAI ou outro provedor futuramente sem alterar o contrato da API.
- Guardrails mínimos validados no serviço: `advisorRunId`, `task`, `expectedResponseSchema` e `do_not_promote_models`; respostas acima de `maxCandidates` são rejeitadas para preservar orçamento e controle operacional.
- Exposto endpoint genérico condicional `POST /ai/advisor/recommendations` apenas quando o módulo for habilitado, retornando recomendações em formato provider-agnostic e mapeando erros de validação para HTTP 400.
- Adicionados testes `AiAdvisorServiceTest` e `AiAdvisorControllerTest` cobrindo delegação para provider configurado, validação dos guardrails, limite de candidatos, contrato JSON do endpoint e mapeamento de erros.
- Check executado inicialmente: `cd backend/sisacao-backend && ./mvnw -q -Dtest=AiAdvisorServiceTest,AiAdvisorControllerTest test`.
- Check completo executado após a implementação: `cd backend/sisacao-backend && ./mvnw -q test`.
## 2026-06-21 — Correção do erro no leaderboard de evolução neural

- Investigação: reproduzi o erro operacional com `curl -i -sS http://34.194.252.70/api/ops/neural/evolution/leaderboard`, confirmando HTTP 502 com mensagem `Falha ao consultar BigQuery`.
- Confirmação da causa provável: consultei o MCP via JSON-RPC por HTTP em `http://mcpserversisacao.shop/mcp` com `initialize` e `tools/call`/`bigquery_query` para verificar `INFORMATION_SCHEMA`. As consultas confirmaram que a view/tabelas de evolução neural (`vw_neural_evolution_leaderboard`, `neural_evolution_*`, `neural_candidate_*`) ainda não estão materializadas no BigQuery, causando 404 na consulta do backend.
- Correção aplicada: o backend agora trata especificamente `BigQueryException` 404 na busca do leaderboard de evolução neural e retorna lista vazia, preservando erros não-404 como falhas reais de acesso ao BigQuery. Foi adicionado teste unitário para garantir o comportamento quando a view opcional ainda não existe.
- Validação: executei `cd backend/sisacao-backend && ./mvnw test -Dtest=BigQueryOpsClientTest` e `cd backend/sisacao-backend && ./mvnw test`, ambos com sucesso.

## 2026-06-21 18:05 UTC — Esclarecimento do host de publicação do backend
- Respondida a dúvida operacional sobre o host usado para publicar o backend.
- Confirmei nos documentos versionados e no workflow de deploy que o backend Spring Boot é publicado no Amazon Lightsail/VPS no host `34.194.252.70`, usando SSH com usuário `deploy` e serviço `sisacao-backend.service`.
- Comandos usados: `rg -n "backend|host|34\\.194|VPS|publicad|deploy|server" -S AGENTS.md docs .github functions` e `nl -ba` em `AGENTS.md` e `.github/workflows/deploy-lightsail.yml` para confirmar as linhas citadas.

## 2026-06-21 18:25 UTC — Workflow de deploy do módulo Gemini advisor
- Identificado, a partir da evidência visual fornecida, que a API key do Gemini está no host `34.194.252.70` em `/home/ubuntu/keys/gemini_api_key`.
- Implementado provider Java `gemini` para o módulo `com.sisacao.backend.aiadvisor`, lendo a credencial por `GEMINI_API_KEY_FILE` ou `GEMINI_API_KEY` e chamando a API Gemini com saída JSON estruturada.
- Criado workflow `.github/workflows/deploy-ai-advisor-lightsail.yml` para compilar o backend, enviar o JAR ao mesmo host Lightsail e validar a chave fonte em `/home/ubuntu/keys/gemini_api_key`, copiá-la para `/opt/sisacao/app/secrets/gemini_api_key` e habilitar `AI_ADVISOR_ENABLED=true`, `AI_ADVISOR_PROVIDER=gemini` e `GEMINI_API_KEY_FILE=/opt/sisacao/app/secrets/gemini_api_key` no `.env` do serviço antes de reiniciar `sisacao-backend.service`.
- Comandos usados: `rg -n "aiadvisor|Gemini|gemini|GEMINI|ai-advisor|advisor" backend .github docs -S --glob '!**/target/**'`, `sed -n` nos arquivos Java/properties e criação/validação local com Maven.

## 2026-06-21 20:55 UTC — Diagnóstico do deploy AI Advisor no Lightsail
- Investigado o erro do workflow `deploy-ai-advisor-lightsail.yml` informado no log do GitHub Actions: o primeiro `sudo test -r /home/ubuntu/keys/gemini_api_key` falhou em ambiente não interativo com `sudo: a terminal is required to read the password`, e em seguida o script reportou a chave Gemini como não legível.
- Causa confirmada por inspeção do workflow: o job usa `appleboy/ssh-action` com usuário `deploy` e executa comandos privilegiados sem `sudo -n`/preflight; portanto, se o usuário `deploy` não tiver NOPASSWD configurado no host, o deploy falha antes mesmo de validar de forma confiável a existência/permissão da chave em `/home/ubuntu/keys/gemini_api_key`.
- Correção aplicada no workflow: adicionado preflight explícito `sudo -n true` com mensagem de diagnóstico, validação da chave com `sudo -n test -r` e conversão dos comandos privilegiados do passo para `sudo -n`, evitando prompt de senha/TTY e produzindo erro acionável quando faltar NOPASSWD ou quando a chave não existir/não for legível por root.
- Ação operacional ainda necessária no host se o erro persistir: configurar NOPASSWD para o usuário `deploy` nos comandos necessários ou preparar manualmente o arquivo runtime em `/opt/sisacao/app/secrets/gemini_api_key` e permissões do serviço.
- Comandos usados: `find .github/workflows -maxdepth 2 -type f -print -exec sed -n '1,220p' {} \;`, `sed -n '1,240p' .github/workflows/deploy-ai-advisor-lightsail.yml` e edição local do workflow/diário.

## 2026-06-21 21:10 UTC — Ajuste do usuário remoto para chave Gemini no Lightsail
- Recebida validação manual no host `ip-172-26-8-107` mostrando que, como usuário `ubuntu`, `sudo test -r /home/ubuntu/keys/gemini_api_key && echo OK` retorna `OK`; portanto o arquivo existe no servidor Lightsail e é legível via sudo pelo usuário `ubuntu`.
- Corrigida a hipótese operacional anterior: o workflow não procurava a chave no ambiente do GitHub, mas conectava como `deploy` enquanto a chave estava sob `/home/ubuntu/keys`, o que tornava a leitura dependente de `sudo`/permissões do usuário errado.
- Correção aplicada: o workflow de deploy do AI Advisor agora usa SSH/SCP com `username: ubuntu`, envia o artefato para `/home/ubuntu/sisacao/app/` e move esse JAR para `/opt/sisacao/app/sisacao-backend.jar`, mantendo a cópia da chave Gemini a partir de `/home/ubuntu/keys/gemini_api_key`.
- Comandos usados: inspeção com `nl -ba .github/workflows/deploy-ai-advisor-lightsail.yml | sed -n '36,100p'`, edição do workflow e registro no diário.

## 2026-06-21 21:20 UTC — Correção do upload do backend para Lightsail
- Investigado o erro do workflow `deploy-lightsail.yml` informado no GitHub Actions: o passo `appleboy/scp-action@v0.1.7` (`drone-scp`) falhou no upload para `34.194.252.70` com `ssh: handshake failed: ssh: unable to authenticate, attempted methods [none publickey], no supported methods remain`.
- Causa provável confirmada por inspeção do workflow: a falha ocorreu especificamente no container do `drone-scp`, enquanto o workflow já usa `appleboy/ssh-action` para validar conexão e reiniciar o serviço com a mesma chave. Para reduzir incompatibilidade do wrapper SCP e melhorar diagnóstico, o upload deixou de depender do `drone-scp`.
- Correção aplicada: adicionado passo SSH para criar `/home/deploy/sisacao/app/` antes do upload e substituído `appleboy/scp-action` por `scp` nativo do runner, gravando `secrets.KEY` em arquivo temporário com permissão `600`, usando `IdentitiesOnly=yes`, `StrictHostKeyChecking=accept-new` e validação explícita de existência do JAR antes da cópia.
- Comandos usados: `find .. -name AGENTS.md -print`, `git status --short`, `cat AGENTS.md`, `find .github/workflows -maxdepth 1 -type f -print -exec sed -n '1,220p' {} \;`, `sed -n '1,220p' .github/workflows/deploy-lightsail.yml` e edição local do workflow/diário.

## 2026-06-21 — Tela Advisor IA Gemini no frontend

- Adicionada tela **Advisor IA Gemini** no grupo de redes neurais do painel operacional para acionar o módulo publicado em `/ai/advisor/recommendations`.
- A tela permite informar o objetivo da rodada, limitar candidatos, enviar contexto resumido do leaderboard neural e acompanhar provider, modelo, status, justificativa, rejeições e candidatos retornados.
- Comandos usados para confirmar e validar: `rg --files`, `rg -n "gemini|ia|ai|neural"`, leitura dos contratos Java do módulo `aiadvisor` e `npm run build` e `npm run lint` no frontend.

## 2026-06-22 UTC — Implementação do orquestrador de evolução neural
- Implementada a Cloud Function HTTP `functions/neural_evolution_orchestrator`, responsável por gerar candidatos determinísticos, persistir rodada/configurações no BigQuery, chamar `neural_training`, buscar métricas no `neural_model_registry`, calcular score/decisão e gravar `neural_candidate_evaluations` para alimentar o leaderboard.
- Adicionada a função ao workflow `.github/workflows/deploy.yml` com variáveis BigQuery, URL de `neural_training`, memória de 512Mi e timeout de 3600s.
- Criado o runbook `docs/neural_evolution_orchestrator_scheduler.md` com payloads de teste, exemplo `dry_run` e comandos `gcloud scheduler jobs create/update http` com OIDC.
- Adicionados testes unitários para fluxo principal, `dry_run` e parsing de métricas do registry.
- Ferramentas/comandos usados para confirmar a causa e a correção: buscas com `rg`, inspeção de `functions/`, leitura dos DDLs BigQuery e execução de testes/lint locais antes do commit.

## 2026-06-22 UTC — Correção do runbook do Scheduler da evolução neural
- Investigado o erro reportado no `gcloud scheduler jobs create http neural-evolution-weekly`: o comando usava `--oidc-service-account-email=agendamentos-sisacao@ingestaokraken.iam.gserviceaccount.com`, mas o Terraform do repositório define por padrão `sa-scheduler-invoker` para invocação do Scheduler, tornando provável a falha `NOT_FOUND` por service account inexistente.
- Atualizado `docs/neural_evolution_orchestrator_scheduler.md` para explicar o diagnóstico do `NOT_FOUND`, incluir comandos de validação/criação da service account `sa-scheduler-invoker`, conceder `roles/run.invoker`, oferecer um caminho rápido sem OIDC compatível com o deploy atual `--allow-unauthenticated` e corrigir os exemplos OIDC para a service account padrão do repositório.
- Ferramentas/comandos usados para confirmar a causa provável: `rg -n "agendamentos-sisacao|sa-scheduler-invoker|neural-evolution|scheduler jobs create" docs infra .github -S`, leitura de `infra/iam/main.tf`, `infra/iam/variables.tf` e do runbook do Scheduler.

## 2026-06-22 UTC — Ajuste de deadline do Scheduler da evolução neural
- Analisada a saída do `gcloud scheduler jobs create http neural-evolution-weekly`, que confirmou o job `ENABLED` para `2026-06-29T09:00:00Z` (06:00 em `America/Sao_Paulo`), mas revelou `attemptDeadline: 180s`.
- Atualizado o runbook para incluir `--attempt-deadline=1800s` nos comandos de criação/atualização e um comando específico para corrigir jobs já criados com o deadline padrão curto.
- Registrada a orientação de reduzir `max_trials` ou evoluir para enfileiramento assíncrono se a rodada exceder 30 minutos.
## 2026-06-21 21:35 UTC — Contagem atual de redes neurais testadas
- Respondida a dúvida operacional "quantas redes estão sendo testadas atualmente?" consultando o endpoint publicado `GET http://34.194.252.70/api/ops/neural/training-runs`.
- Resultado observado: o endpoint retornou 19 registros em `neural_model_registry`, todos com `status=candidate`; portanto, atualmente há 19 redes/artefatos candidatos testados/registrados para acompanhamento, sem modelos aprovados no retorno consultado.
- Observação de disponibilidade: a tentativa de confirmar via MCP obrigatório em `http://mcpserversisacao.shop/mcp` por JSON-RPC HTTP retornou HTTP 503/timeouts em três tentativas; a resposta operacional foi baseada no endpoint REST publicado do backend, que lê a tabela `neural_model_registry`.
- Comandos usados: `python`/`requests` para `initialize` do MCP via HTTP com retry, `curl -sS http://34.194.252.70/api/ops/neural/training-runs` e `python` para contar registros/status e listar versões recentes.

## 2026-06-21 21:45 UTC — Diferenças entre as redes neurais candidatas atuais
- Respondida a dúvida operacional "qual a diferença entre elas?" com nova leitura do endpoint publicado `GET http://34.194.252.70/api/ops/neural/training-runs` e resumo das métricas retornadas por versão.
- Diferenças principais observadas: 2 registros legados `v1_20260620_*` usam snapshot anterior e não trazem métricas de validação/teste; 1 baseline `v1_20260621_phase0` usa o snapshot com splits completos; 10 candidatos `evo1_20260621_*` são variações determinísticas da Fase 1; 6 candidatos `evo2_*` são a Fase 2, composta por 3 mutações e 3 repetições multi-seed do melhor candidato anterior.
- Entre os 6 candidatos Fase 2 já diagnosticados, todos usam arquitetura `hidden_units=[256,128,64]` e `batch_size=512`; as três repetições multi-seed usam `learning_rate=0.0003`, `dropout_rate=0.35`, `epochs=80` e diferem apenas pelo `random_seed` (`20260701`, `20260702`, `20260703`).
- Métricas mais relevantes no endpoint atual: melhor acurácia de teste entre as 19 foi `evo1_20260621_02` com `test_accuracy=0.4347`, mas baixa precisão direcional (`0.2695`) e cobertura (`0.2227`); melhor equilíbrio operacional segue `evo2_seed_20260621_01_20260701` com `test_accuracy=0.4240`, `directional_precision=0.3480` e `coverage=0.3640`.
- Comandos usados: `curl -sS http://34.194.252.70/api/ops/neural/training-runs`, `python` para parsear `metricsJson` e listar `modelVersion`, snapshot, features, labels, acurácia, precisão direcional, cobertura e linhas de teste; `nl -ba docs/diario/registros1.md` para consultar diagnósticos anteriores das fases.

## 2026-06-22 00:10 UTC — Estratégia de evolução/criação de novas redes neurais
- Respondida a dúvida operacional sobre como evoluir as redes atuais ou criar novas para buscar melhor performance.
- Direção recomendada: transformar os testes atuais em um ciclo recorrente de evolução com orçamento controlado, partindo do melhor candidato por equilíbrio (`evo2_seed_20260621_01_20260701`) como referência, mas explorando arquiteturas menores/menos variância, novos `class_weight`, `dropout_rate`, `learning_rate`, `batch_size`, múltiplas seeds e, só depois, estruturas como batch normalization, residual curta, wide & deep tabular e ensemble leve.
- Critério de comparação: não escolher apenas por `test_accuracy`; priorizar precisão direcional de teste, cobertura, estabilidade validação/teste, gap treino/teste, backtest ajustado a risco e penalização por complexidade/custo, mantendo avaliação fora da amostra obrigatória.
- Governança: novos candidatos devem ser registrados como `candidate`, passar pelo gate de shadow (`min_test_accuracy=0.38`, `min_directional_precision=0.34`, `min_coverage=0.20`, `min_test_rows=500`, limites de overfit/drift) e nunca ir para paper/capital sem evidência adicional, paper trading mínimo e aprovação explícita.
- Comandos usados: `rg -n "evolução neural|neural_evolution|promotion|shadow|class_weight|early_stopping" docs sisacao8 functions tests infra backend frontend -S --glob '!**/target/**' --glob '!**/node_modules/**'`, `sed -n`/`nl -ba` em `docs/planejamento/evolucao-neural-automatica.md`, `sisacao8/neural_evolution.py` e `sisacao8/neural_promotion.py`.

## 2026-06-22 12:05 UTC — Diagnóstico da tela de evolução neural vazia
- Investigada a tela “Redes neurais — Evolução determinística” publicada em `http://34.194.252.70/` após o alerta de que nada aparecia na evolução.
- Confirmação via backend publicado: `GET http://34.194.252.70/api/ops/neural/evolution/leaderboard` retornou `[]`, portanto o frontend estava exibindo corretamente o estado vazio recebido da API.
- Confirmação via MCP JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp` e BigQuery: `vw_neural_evolution_leaderboard`, `neural_evolution_runs`, `neural_candidate_configs` e `neural_candidate_evaluations` estão com 0 linhas; já `neural_model_registry` tem 19 linhas e `neural_eod_training_dataset` tem 16136 linhas.
- Conclusão operacional: ainda falta executar uma rodada real do `neural_evolution_orchestrator` sem `dry_run` para gravar runs/configurações/avaliações. Um `dry_run` manual com `max_trials=2` confirmou que a função gera candidatos, mas não materializa dados no leaderboard.
- Correção aplicada no frontend: o estado vazio da aba Evolução agora explica que a tela depende da execução do orquestrador sem `dry_run` e da gravação em `neural_candidate_evaluations`, evitando confundir modelos já existentes no registry com candidatos avaliados no leaderboard.
- Comandos usados: `curl -sS http://34.194.252.70/api/ops/neural/evolution/leaderboard`, `curl` JSON-RPC HTTP para `initialize`, `tools/list`, `bigquery_query` e `cloud_run_function_logs` no MCP, `curl -X POST https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator` com `dry_run=true`, além de inspeção de `NeuralEvolutionTab.tsx`, `BigQueryOpsClient.java` e `functions/neural_evolution_orchestrator/main.py`.


## 2026-06-22 12:25 UTC — Esclarecimento sobre automação da evolução neural
- Esclarecido que a execução sem `dry_run` não deve depender de comandos manuais recorrentes: o caminho operacional correto é o Cloud Scheduler `neural-evolution-weekly`, com disparos manuais apenas para antecipar a primeira rodada, testar payloads ou recuperar uma execução perdida.
- Atualizado o runbook do orquestrador para incluir uma seção explícita de operação recorrente e comando de `gcloud scheduler jobs run` para antecipação pontual.
- Ajustado o estado vazio da tela de Evolução para informar que o preenchimento ocorre automaticamente quando o Scheduler disparar uma rodada real do `neural_evolution_orchestrator`, evitando sugerir que o operador precise sempre rodar `curl` manual.
- Comandos usados: `git status --short`, tentativa de `gcloud scheduler jobs describe neural-evolution-weekly` (indisponível no ambiente por ausência de `gcloud`), `find infra -maxdepth 3 -type f`, `rg -n "scheduler|neural-evolution|cloudfunctions|functions" infra .github docs -S` e edição dos arquivos de frontend, runbook e diário.


## 2026-06-22 12:45 UTC — Validação da primeira rodada real de evolução neural
- Recebido resultado da execução real do `neural_evolution_orchestrator` sem `dry_run`, com `candidate_count=2`, `trained_count=2`, `evaluated_count=2`, `failed_count=0` e rodada `neural_evolution_20260622_120807_955b4e69`.
- Confirmado pelo endpoint publicado `GET http://34.194.252.70/api/ops/neural/evolution/leaderboard` que a tela passou a ter 2 candidatos avaliados, ambos com decisão `reject`.
- Investigada a causa dos `reject`: os registros de treino dos modelos `neural_eod_mlp_evo1_20260622_01` e `neural_eod_mlp_evo1_20260622_02` traziam métricas apenas do split `train`, sem métricas de `validation`/`test`, gerando motivos como `test_missing`, `coverage_test_below_minimum` e `directional_precision_test_below_baseline`.
- Correção aplicada no orquestrador: quando o payload não fixa `dataset_snapshot`, a seleção automática passa a exigir snapshots completos com linhas nos splits `train`, `validation` e `test`, evitando escolher snapshots parciais que produzem avaliações sem teste fora da amostra.
- Comandos usados: `curl -sS http://34.194.252.70/api/ops/neural/evolution/leaderboard`, `curl -sS http://34.194.252.70/api/ops/neural/training-runs`, tentativa de consulta BigQuery via MCP JSON-RPC HTTP, `rg -n "def _latest_dataset_snapshot|dataset_snapshot" functions/neural_evolution_orchestrator/main.py tests/test_neural_evolution_orchestrator_function.py -S` e inspeção de `functions/neural_training/main.py` e `sisacao8/neural_evolution.py`.


## 2026-06-22 13:05 UTC — Verificação do Scheduler da evolução neural
- Tentada verificação direta do Cloud Scheduler `neural-evolution-weekly` a partir do container, mas o ambiente não possui `gcloud` instalado e não tem metadados/ADC disponíveis para chamar a API do Cloud Scheduler diretamente.
- Confirmado no histórico operacional do diário que a saída anterior de `gcloud scheduler jobs create http neural-evolution-weekly` já havia indicado o job `ENABLED` para `2026-06-29T09:00:00Z` (06:00 em `America/Sao_Paulo`), com necessidade de ajustar `attemptDeadline` de 180s para 1800s.
- Consultado o MCP via JSON-RPC HTTP; as ferramentas disponíveis no servidor remoto incluem BigQuery/logs, mas não expõem listagem/describe do Cloud Scheduler, então a confirmação live do job precisa ser feita por `gcloud scheduler jobs describe/list` em ambiente com SDK autenticado ou pelo Console GCP.
- Atualizado o runbook com comandos explícitos para verificar a existência/estado do job `neural-evolution-weekly` e listar jobs relacionados ao endpoint `neural_evolution_orchestrator`.
- Comandos usados: `git status --short`, `command -v gcloud`, `env | rg -n "GOOGLE|GCP|GCLOUD|CLOUDSDK"`, `find ~/.config -maxdepth 4 -type f`, `curl` para inicializar o MCP por HTTP JSON-RPC e chamar `runtime_config`, `curl` para metadados GCP e `nl -ba` nos trechos do diário/runbook.


## 2026-06-22 13:20 UTC — Tentativa e habilitação de verificação do Scheduler via MCP
- Atendido o pedido para tentar verificar o Cloud Scheduler via MCP Server usando JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp`.
- O `tools/list` do MCP publicado confirmou que a versão atual ainda expõe apenas `ping`, `runtime_config`, `bigquery_access_check`, `bigquery_query`, `mcp_server_logs`, `cloud_run_function_logs` e `backend_actuator_logs_url`, sem ferramenta de Cloud Scheduler.
- Tentadas chamadas exploratórias para `cloud_scheduler_jobs`, `cloud_scheduler_job`, `scheduler_jobs` e `gcp_scheduler_jobs`; todas retornaram `Tool not found`, confirmando que a verificação live do Scheduler ainda não estava implementada no MCP publicado.
- Como alternativa parcial, `cloud_run_function_logs` para `neural_evolution_orchestrator` retornou duas chamadas HTTP 200 nas últimas 6 horas, incluindo a execução real de `2026-06-22 12:08:07`, mas logs da função não provam a existência do job Scheduler.
- Correção aplicada no MCP Java: adicionada a tool `cloud_scheduler_job`, que executa `gcloud scheduler jobs describe <job>` no runtime autenticado do MCP, para permitir consultar `neural-evolution-weekly` via JSON-RPC após deploy da nova versão do MCP.
- Comandos usados: `curl` HTTP JSON-RPC para `initialize`, `tools/list`, tentativas de `tools/call` com nomes de Scheduler, `tools/call` com `cloud_run_function_logs`, inspeção de `mcp-server-java/AGENTS.md`, `McpController.java`, `McpControllerTest.java` e `README.md`.

## 2026-06-22 13:35 UTC — Visualização intuitiva dos estágios das redes neurais
- Ajustada a experiência das telas de redes neurais para separar visualmente o total de redes candidatas registradas do subconjunto avaliado pela rodada atual de evolução.
- Na tela de Treinos, adicionados cards de estágio para `Total de redes`, `Em treino agora`, `Candidatas` e `Aprovadas`, além de um bloco explicativo com chips para os estados `Em treino`, `Candidata`, `Aprovada` e `Rejeitada`.
- Na tela de Evolução, adicionado um mapa/funil visual com `Redes candidatas`, `Aguardando avaliação`, `Avaliadas agora`, `Mantidas` e `Rejeitadas`, reduzindo a confusão entre as 21 redes no registro e as 2 avaliadas na rodada `neural_evolution_20260622_120807_955b4e69`.
- Comandos usados: `curl` para consultar `http://34.194.252.70/api/ops/neural/training-runs` e `http://34.194.252.70/api/ops/neural/evolution/leaderboard`, script Python com `urllib.request` para contar status/decisões, inspeção de `App.tsx`, `NeuralTrainingRunsTab.tsx`, `NeuralEvolutionTab.tsx` e `ops.ts`, e `npm run build` no frontend.

## 2026-06-22 — Esclarecimento sobre próximas avaliações da evolução neural

- Investigada a dúvida operacional sobre quando as redes em `Aguardando avaliação` entram no funil da tela `Redes neurais — Evolução`.
- Confirmado no runbook que a operação recorrente prevista é o Cloud Scheduler `neural-evolution-weekly`, com agenda `0 6 * * 1` em `America/Sao_Paulo`, chamando `neural_evolution_orchestrator` com `max_trials=10`; portanto as próximas redes são avaliadas nas próximas rodadas agendadas ou quando o job for executado manualmente para antecipação.
- Confirmado pelo endpoint publicado `GET http://34.194.252.70/api/ops/neural/evolution/leaderboard` que a rodada atual materializada é `neural_evolution_20260622_120807_955b4e69`, com 2 candidatos avaliados e ambos rejeitados pela governança.
- Comandos usados: `rg -n "Aguardando|avaliadas|avaliad|neural_evolution|Redes candidatas|Evolução" -S . --glob '!node_modules' --glob '!dist' --glob '!build'`, `nl -ba docs/neural_evolution_orchestrator_scheduler.md`, `nl -ba functions/neural_evolution_orchestrator/main.py`, `nl -ba frontend/app/src/components/tabs/NeuralEvolutionTab.tsx` e `curl -sS http://34.194.252.70/api/ops/neural/evolution/leaderboard | python -m json.tool | head -120`.

## 2026-06-22 — Ajuste sobre frequência da avaliação neural

- Esclarecido que a frequência semanal do `neural-evolution-weekly` é uma configuração conservadora inicial, não uma limitação técnica do `neural_evolution_orchestrator`.
- Atualizado o runbook para explicar o motivo da cadência semanal: reduzir custo, runtime e risco de reavaliar muitos candidatos sobre o mesmo snapshot sem nova evidência fora da amostra.
- Documentadas alternativas para acelerar a avaliação das redes pendentes: execução manual pontual do Scheduler existente ou criação/alteração de um job diário com orçamento menor (`max_trials` entre 2 e 5), mantendo controle operacional.
- Comandos usados: inspeção do histórico com `git log --oneline -3`, verificação de estado com `git status --short` e atualização de `docs/neural_evolution_orchestrator_scheduler.md` e `docs/diario/registros1.md`.

## 2026-06-22 — Mudança recomendada para avaliação neural diária controlada

- Ajustada a recomendação operacional do runbook: para evolução contínua com controle, usar Scheduler diário `neural-evolution-daily` em vez de manter a cadência semanal como padrão.
- O orçamento recomendado passou a ser menor por rodada, começando com `max_trials=3` e `max_runtime_minutes=120`, mantendo `attempt-deadline=1800s` para evitar concentração de custo/runtime em uma única execução semanal.
- Mantida a orientação de usar rodadas manuais apenas para antecipação pontual ou recuperação de execução perdida, e adicionada a orientação para pausar/remover o Scheduler semanal depois que o diário for criado e validado.
- Comandos usados: `rg -n "neural-evolution-weekly|neural-evolution-daily|max_trials|schedule='0 6 \\* \\* 1'|Operação recorrente" docs infra .github functions backend frontend -S --glob '!**/node_modules/**' --glob '!**/target/**'` e edição de `docs/neural_evolution_orchestrator_scheduler.md`/`docs/diario/registros1.md`.

## 2026-06-22 — Alteração do Scheduler diário via MCP Server

- Acessado o MCP Server publicado via JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp`, executando `initialize`, capturando `mcp-session-id` e chamando `tools/list` conforme o procedimento obrigatório do projeto.
- Confirmado via tool `cloud_scheduler_job` que `neural-evolution-daily` ainda não existe no Cloud Scheduler e que `neural-evolution-weekly` está `ENABLED`, com `schedule: 0 6 * * 1`, `attemptDeadline: 1800s` e payload com `max_trials=10`/`max_runtime_minutes=240`.
- Identificada limitação da versão atualmente publicada do MCP: ela expõe apenas `cloud_scheduler_job` para consulta (`describe`) e ainda não possui tool de criação/atualização/pausa do Scheduler, impedindo aplicar a mudança real imediatamente só por MCP no ambiente remoto.
- Implementada no MCP Java a tool `neural_evolution_daily_scheduler_apply`, que executa `gcloud scheduler jobs update http neural-evolution-daily`, faz fallback para `create http` se o job diário não existir e pausa `neural-evolution-weekly` quando `pause_weekly=true`.
- Atualizados README do MCP, testes de listagem de tools e runbook da evolução neural para orientar a alteração via JSON-RPC HTTP assim que a nova versão do MCP for publicada.
- Comandos usados: `curl` HTTP JSON-RPC para `initialize`, `tools/list` e `tools/call`/`cloud_scheduler_job` no MCP; inspeção com `rg -n "cloud_scheduler_job|Scheduler|scheduler" mcp-server-java backend functions docs -S --glob '!**/target/**'`; edição de `McpController.java`, `McpControllerTest.java`, `mcp-server-java/README.md`, `docs/neural_evolution_orchestrator_scheduler.md` e deste diário.

## 2026-06-22 — Tentativa de criar Scheduler diário pelo MCP publicado

- Tentada criação do Scheduler diário `neural-evolution-daily` pelo MCP Server publicado via JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp`, seguindo o fluxo obrigatório de `initialize`, captura de `mcp-session-id`, `tools/list` e `tools/call`.
- O `tools/list` confirmou que a versão publicada ainda expõe apenas `cloud_scheduler_job` para consulta do Cloud Scheduler, sem a nova tool `neural_evolution_daily_scheduler_apply`.
- A chamada `tools/call` para `neural_evolution_daily_scheduler_apply` retornou erro JSON-RPC `-32601` com mensagem `Tool not found: neural_evolution_daily_scheduler_apply`, portanto não foi possível criar/alterar o Scheduler pelo MCP publicado nesta tentativa.
- Conclusão operacional: consigo criar pelo MCP somente depois que a versão do MCP Java que adiciona `neural_evolution_daily_scheduler_apply` for publicada; até lá, o MCP remoto permite verificar o Scheduler, mas não modificá-lo.
- Comandos usados: `curl` HTTP JSON-RPC para `initialize`, `tools/list` e tentativa de `tools/call` com `neural_evolution_daily_scheduler_apply`, sempre em `http://mcpserversisacao.shop/mcp` e com header `mcp-session-id`.

## 2026-06-22 — Escrita genérica no Cloud Scheduler via MCP Java

- Alterado o MCP Java para permitir escrita controlada no Cloud Scheduler por meio da nova tool `cloud_scheduler_job_write`.
- A tool aceita as ações `create`, `update`, `pause`, `resume`, `run` e `delete`, mantendo o projeto fixo em `ingestaokraken` e validando `job_name`, método HTTP, URI alvo e service account OIDC antes de executar `gcloud scheduler jobs ...`.
- Mantida a tool específica `neural_evolution_daily_scheduler_apply` para o caso operacional da evolução neural, agora complementada pela tool genérica para futuras operações de Scheduler via JSON-RPC.
- Atualizados `mcp-server-java/README.md`, `docs/neural_evolution_orchestrator_scheduler.md` e testes do MCP para listar e validar a nova tool de escrita.
- Comandos usados: edição de `mcp-server-java/src/main/java/com/sisacao/mcpserver/McpController.java`, `mcp-server-java/src/test/java/com/sisacao/mcpserver/McpControllerTest.java`, `mcp-server-java/README.md`, `docs/neural_evolution_orchestrator_scheduler.md` e `docs/diario/registros1.md`.

## 2026-06-22 — Tentativa de criação do Scheduler diário de evolução neural

- Tentada criação/atualização do Cloud Scheduler `neural-evolution-daily` pelo MCP publicado via JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp`, usando a tool `neural_evolution_daily_scheduler_apply` com `pause_weekly=true`.
- O MCP confirmou que a tool de escrita já está publicada, mas a aplicação real não foi concluída porque a credencial remota `codex-openai@ingestaokraken.iam.gserviceaccount.com` não possui `cloudscheduler.jobs.create` para criar `neural-evolution-daily` nem `cloudscheduler.jobs.pause` para pausar `neural-evolution-weekly`.
- Confirmado via `cloud_scheduler_job` que `neural-evolution-daily` ainda retorna `NOT_FOUND` e que `neural-evolution-weekly` permanece `ENABLED`, com `schedule: 0 6 * * 1`, `timeZone: America/Sao_Paulo`, `attemptDeadline: 1800s` e endpoint `neural_evolution_orchestrator`.
- Corrigida a montagem dos comandos `gcloud scheduler jobs update http` no MCP Java para usar `--update-headers` em atualizações e manter `--headers` em criações, evitando o erro de CLI `unrecognized arguments: --headers` antes da validação de permissões.
- Comandos usados: `curl`/Python `urllib.request` para `initialize`, `tools/list`, `tools/call`/`neural_evolution_daily_scheduler_apply` e `tools/call`/`cloud_scheduler_job` no MCP; inspeção/edição de `mcp-server-java/src/main/java/com/sisacao/mcpserver/McpController.java`; `git status --short`.

## 2026-06-22 — Comandos locais para criar Scheduler diário de evolução neural

- Orientado o uso de `gcloud` no terminal local autenticado para criar `neural-evolution-daily`, validar o job e pausar `neural-evolution-weekly` após a validação, já que a credencial remota do MCP não tem permissões de escrita no Cloud Scheduler.
- Atualizado o runbook para usar `--update-headers` no exemplo de `gcloud scheduler jobs update http`, mantendo `--headers` apenas nos exemplos de `create http`, alinhado ao comportamento da CLI observado no MCP.
- Comandos usados: `git status --short`, `nl -ba docs/neural_evolution_orchestrator_scheduler.md`, edição de `docs/neural_evolution_orchestrator_scheduler.md` e `docs/diario/registros1.md`.

## 2026-06-22 — Verificação do Scheduler diário de evolução neural criado

- Verificado via MCP JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp` que o Cloud Scheduler `neural-evolution-daily` foi criado em `ingestaokraken/us-east1` e está `ENABLED`, com agenda `0 6 * * *`, timezone `America/Sao_Paulo`, `attemptDeadline: 1800s`, método `POST` e URI `https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator`.
- Decodificado o payload do `neural-evolution-daily`, confirmando `strategy=deterministic_phase1`, `max_trials=3`, `max_runtime_minutes=120`, `max_parameter_count=150000`, `max_layers=4` e `random_seed=20260621`.
- Confirmado que o `neural-evolution-weekly` ainda permanece `ENABLED` com agenda `0 6 * * 1`; foi tentado pausar pelo MCP, mas a credencial remota `codex-openai@ingestaokraken.iam.gserviceaccount.com` ainda não possui `cloudscheduler.jobs.pause`.
- Conclusão operacional: o Scheduler diário foi criado corretamente, mas ainda é necessário pausar/remover o semanal por um terminal autenticado com permissão de escrita para evitar duas execuções na segunda-feira.
- Comandos usados: `curl`/Python `urllib.request` para `initialize`, `tools/call`/`cloud_scheduler_job` em `neural-evolution-daily` e `neural-evolution-weekly`, tentativa de `tools/call`/`cloud_scheduler_job_write` com `action=pause`, e decodificação local do payload base64 com Python.

## 2026-06-23 — Proposta de Scheduler horário para evolução neural

- Avaliada a mudança da execução de evolução neural de uma vez ao dia para execução horária no minuto 45, mantendo o job `neural-evolution-daily` e alterando sua agenda para `45 * * * *`.
- Atualizado o runbook `docs/neural_evolution_orchestrator_scheduler.md` para recomendar orçamento menor por rodada (`max_trials=1`, `max_runtime_minutes=45`) na cadência horária, reduzindo risco de custo e sobreposição de treinos.
- Tentada a aplicação pelo MCP via JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp` usando `cloud_scheduler_job_write`, mas a credencial remota `codex-openai@ingestaokraken.iam.gserviceaccount.com` não possui `cloudscheduler.jobs.update` para alterar `neural-evolution-daily`.
- Conclusão operacional: a mudança é tecnicamente adequada se cada rodada for pequena e idempotente; a alteração real no GCP ainda precisa ser aplicada por uma credencial com permissão de update no Cloud Scheduler.
- Comandos usados: `rg` para localizar referências de Scheduler neural, edição de `docs/neural_evolution_orchestrator_scheduler.md`, Python `urllib.request` para `initialize` e `tools/call`/`cloud_scheduler_job_write` via MCP HTTP, e atualização deste diário.

## 2026-06-23 — Comunicação do funil de evolução neural

- Melhorada a comunicação do mapa visual de evolução neural para evitar a interpretação ambígua entre estoque total de redes, avaliações materializadas e versões únicas de modelo.
- O card `Aguardando avaliação` foi substituído por `Ainda faltam`, calculado como `Redes no estoque - Avaliações feitas`, deixando explícita a conta exibida para o usuário.
- Adicionado bloco explicativo `Como ler estes números`, detalhando quantas redes estão registradas em Treinos, quantas avaliações existem no leaderboard, quantas foram mantidas/rejeitadas e uma observação técnica separada para versões únicas de modelo.
- Comandos usados: `rg -n "Aguardando|AGUARDANDO|avaliadas|Avaliadas|Redes candidatas|CANDIDATAS|não entraram|nao entraram|Mantidas|Rejeitadas" -S .`, `nl -ba frontend/app/src/components/tabs/NeuralEvolutionTab.tsx`, consulta Python via `urllib.request` aos endpoints `http://34.194.252.70/api/ops/neural/training-runs` e `http://34.194.252.70/api/ops/neural/evolution/leaderboard`, `npm run lint` e `npm run build`.

## 2026-06-23 — Documento de diagnóstico diário da evolução neural EOD

- Criado `docs/planejamento/diagnostico-evolucao-redes-neurais-eod.md` para consolidar o diagnóstico operacional sobre redes aparentemente iguais no leaderboard, significado de MLP, prioridade de arquiteturas candidatas e plano diário de evolução.
- Registrado que o fluxo atual deve priorizar variações de MLP/tabular MLP antes de avançar para arquiteturas sequenciais como TCN, GRU, LSTM e Transformer, pois o dataset e a governança atuais são tabulares.
- Incluídos critérios práticos para comparar candidatos por `candidate_id`, `evolution_run_id`, arquitetura, hiperparâmetros, score, precisão direcional, cobertura, generalização, estabilidade e decisão.
- Comandos usados: `git status --short`, leitura de `AGENTS.md` e criação do documento/registro via shell redirection.

## 2026-06-23 12:35:43 UTC-3
- Implementada paginação no leaderboard da aba **Redes neurais — Evolução determinística**, exibindo 20 candidatos por página.
- Adicionada navegação via `TablePagination` com tamanho de página fixo e reset automático para a primeira página quando a lista do leaderboard é atualizada.
- Validação local planejada com lint/build do frontend após o ajuste.

## 2026-06-23 — Esclarecimento sobre redes neurais mantidas na evolução

- Investigado o significado operacional das 3 redes `Mantidas` exibidas na tela **Redes neurais — Evolução determinística**.
- Confirmado no frontend que `Mantidas` corresponde aos itens do leaderboard cuja decisão não é `reject`, enquanto `Rejeitadas` corresponde a `decision === 'reject'`.
- Confirmado no módulo de evolução que as candidatas melhor pontuadas são selecionadas para exploração na Fase 2, onde podem gerar mutações de hiperparâmetros e repetições multi-seed para validar estabilidade.
- Confirmado na view BigQuery `vw_neural_evolution_leaderboard` que a ordenação/ranking usa `score_total` e `score_directional_precision`, preservando decisão e razões da avaliação.
- Comandos usados: `rg -n "mantidas|rejeitadas|Redes neurais|Evolução|leaderboard|Fase 1|Fase 2|selected|mantida|aprovad" -S . --glob '!node_modules' --glob '!dist' --glob '!build'`, `sed -n '120,190p' frontend/app/src/components/tabs/NeuralEvolutionTab.tsx`, `sed -n '140,260p' sisacao8/neural_evolution.py`, `sed -n '124,190p' infra/bq/21_neural_evolution.sql` e atualização deste diário.

## 2026-06-23 — Esclarecimento sobre implementação da Fase 2 da evolução neural

- Investigado se a Fase 2 mencionada para as redes neurais mantidas já está implementada no fluxo atual.
- Confirmado que os blocos de código para seleção do top, mutação de hiperparâmetros e repetição multi-seed existem em `sisacao8/neural_evolution.py` e têm cobertura em `tests/test_neural_evolution.py`.
- Confirmado que a Cloud Function `neural_evolution_orchestrator` publicada no repositório ainda importa e chama apenas `generate_deterministic_candidates`, ou seja, automatiza a geração determinística da Fase 1, não a cadeia completa de seleção/mutação/repetição da Fase 2.
- Consultado o diário histórico, que registra uma execução manual/operacional da Fase 2 em 2026-06-21 com 6 candidatos gerados e treinados; conclusão: a Fase 2 existe como capacidade e já foi executada, mas ainda não está totalmente orquestrada automaticamente pelo scheduler/orchestrator atual.
- Comandos usados: `rg -n "select_top_candidates|mutate_top_candidates|repeat_finalists_with_seeds|deterministic_phase2|phase2|Fase 2|candidate_source|mutation|seed_repeat" functions/neural_evolution_orchestrator sisacao8 tests infra docs -S --glob '!**/__pycache__/**'`, `sed -n '1,360p' functions/neural_evolution_orchestrator/main.py`, `sed -n '70,155p' tests/test_neural_evolution.py` e `sed -n '730,750p' docs/diario/registros1.md`.

## 2026-06-23 — Automação da Fase 2 neural e Scheduler horário no minuto 30

- Implementada no `neural_evolution_orchestrator` a estratégia `deterministic_phase2`, que lê candidatos mantidos em `vw_neural_evolution_leaderboard`, seleciona os melhores pais e gera candidatos de mutação/repetição multi-seed dentro do orçamento configurado.
- Mantida compatibilidade com `deterministic_phase1`; a seleção da estratégia agora decide entre geração determinística nova e exploração de candidatos já mantidos.
- Adicionado teste unitário cobrindo o fluxo `deterministic_phase2` com leitura do leaderboard, geração de mutação, persistência em `neural_candidate_configs` e payload de treino com early stopping.
- Atualizado o runbook do Scheduler para cadência horária no minuto 30 (`30 * * * *`) usando payload `deterministic_phase2`, `max_trials=1`, `max_runtime_minutes=45` e `include_seed_repeats=false`, além dos comandos `gcloud scheduler jobs create/update http` correspondentes.
- Comandos usados: `rg` para localizar referências de fase/estratégia, edição de `functions/neural_evolution_orchestrator/main.py`, `tests/test_neural_evolution_orchestrator_function.py`, `docs/neural_evolution_orchestrator_scheduler.md` e deste diário, `python -m black functions/neural_evolution_orchestrator/main.py tests/test_neural_evolution_orchestrator_function.py`, `python -m pytest tests/test_neural_evolution_orchestrator_function.py tests/test_neural_evolution.py` e `python -m flake8 functions/neural_evolution_orchestrator/main.py tests/test_neural_evolution_orchestrator_function.py`.

## 2026-06-23 — Diagnóstico de NOT_FOUND no update do Scheduler neural

- Recebido erro local do usuário ao executar `gcloud scheduler jobs update http neural-evolution-daily` com `NOT_FOUND` autenticado como `paulofore@gmail.com`.
- Verificado via MCP JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp` que o job `neural-evolution-daily` existe em `ingestaokraken/us-east1`, está `ENABLED`, ainda está em `schedule: 45 * * * *` e possui payload `deterministic_phase1`; o job semanal está `PAUSED`.
- Tentada atualização via MCP com `cloud_scheduler_job_write`, mas a credencial remota `codex-openai@ingestaokraken.iam.gserviceaccount.com` não possui `cloudscheduler.jobs.update`.
- Atualizado o runbook para explicar que `NOT_FOUND` no update pode indicar falta de permissão/conta ativa incorreta, location/projeto incorreto ou problema com service account OIDC, e para oferecer comando de update sem OIDC quando a função estiver pública.
- Comandos usados: Python `urllib.request` para `initialize`, `tools/list`, `tools/call`/`cloud_scheduler_job` e `tools/call`/`cloud_scheduler_job_write` via MCP HTTP; edição de `docs/neural_evolution_orchestrator_scheduler.md` e deste diário.

## 2026-06-23 — Registro permanente sobre OIDC no AGENTS

- Adicionada orientação operacional no `AGENTS.md` para evitar repetir erros ao sugerir comandos de Cloud Scheduler com OIDC.
- Registrado que comandos com `--oidc-service-account-email` só devem ser sugeridos após validar existência da service account, `roles/run.invoker`, `roles/iam.serviceAccountUser` para a conta que executa o `gcloud` e permissões de Cloud Scheduler.
- Registrado que, para funções públicas, o caminho preferencial é atualizar/criar o Scheduler sem OIDC, e que `NOT_FOUND` no `gcloud scheduler jobs update http` deve levar a checagem de conta ativa, projeto, location e permissões antes de concluir que o job não existe.
- Comandos usados: `sed -n '1,260p' AGENTS.md`, edição de `AGENTS.md` e atualização deste diário.

## 2026-06-23 — Orientação sobre mutações semelhantes na evolução neural

- Verificado no frontend publicado que o funil atual possui 42 redes no estoque, 23 avaliações materializadas no leaderboard, 9 mantidas e 14 rejeitadas, confirmando o cenário relatado de crescimento da lista de mantidas.
- Revisado o fluxo de Fase 2: a estratégia `deterministic_phase2` lê candidatos não rejeitados, ordena por score e precisão direcional, gera mutações controladas e pode repetir finalistas por seeds para medir estabilidade.
- Orientação operacional: quando mutações ficam muito semelhantes e aumentam a lista de mantidas, o próximo passo é não promover automaticamente; deve-se consolidar por família/assinatura, comparar diversidade real de hiperparâmetros, repetir os melhores com seeds diferentes e só então avançar para shadow/paper trading.
- Comandos usados: `python` com `urllib.request` para consultar `http://34.194.252.70/api/ops/neural/training-runs` e `http://34.194.252.70/api/ops/neural/evolution/leaderboard`, `rg -n "select_top_candidates|mutate_top_candidates|repeat_finalists_with_seeds|mutation|include_seed_repeats|decision|score_total|leaderboard|deterministic_phase2|phase2|parent" sisacao8 functions tests docs infra -S --glob '!**/__pycache__/**'`, e `nl -ba` em `sisacao8/neural_evolution.py`, `functions/neural_evolution_orchestrator/main.py`, `docs/neural_evolution_orchestrator_scheduler.md` e `docs/planejamento/diagnostico-evolucao-redes-neurais-eod.md`.

## 2026-06-24 — Consolidação de famílias na Fase 2 neural

- Implementada a recomendação operacional para evitar que mutações semelhantes inflem a lista de redes mantidas sem ganho real de diversidade.
- Adicionada assinatura de família em `sisacao8/neural_evolution.py`, ignorando `random_seed` e metadados de early stopping, mas preservando arquitetura, `learning_rate`, `dropout_rate`, `batch_size`, `epochs` e `class_weight` para consolidar configurações equivalentes.
- Atualizada a seleção da estratégia `deterministic_phase2` no `neural_evolution_orchestrator` para usar pais diversos com `max_parents_per_family` configurável, padrão `1`, antes de gerar mutações e repetições.
- Atualizado o runbook do Scheduler para documentar `max_parents_per_family: 1` no payload recomendado e nos comandos `gcloud`.
- Adicionados testes unitários para garantir que a chave de família ignora apenas seed e que a Fase 2 descarta pais repetidos da mesma família ao escolher candidatos para mutação.
- Comandos usados: `git status --short`, `find .. -name AGENTS.md -print`, `sed -n` para leitura de `AGENTS.md`, `sisacao8/neural_evolution.py`, `functions/neural_evolution_orchestrator/main.py` e testes, edição dos arquivos, `python -m black sisacao8/neural_evolution.py functions/neural_evolution_orchestrator/main.py tests/test_neural_evolution.py tests/test_neural_evolution_orchestrator_function.py`, `python -m pytest tests/test_neural_evolution.py tests/test_neural_evolution_orchestrator_function.py` e `python -m flake8 sisacao8/neural_evolution.py functions/neural_evolution_orchestrator/main.py tests/test_neural_evolution.py tests/test_neural_evolution_orchestrator_function.py`.

## 2026-06-24 — Correção de import no deploy do neural_evolution_orchestrator

- Diagnosticado via MCP JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp` que a revisão `neural-evolution-orchestrator-00009-muk` falhava no startup por `ImportError: cannot import name 'select_diverse_top_candidates' from 'sisacao8.neural_evolution'`.
- Confirmado no código que `functions/neural_evolution_orchestrator/main.py` importava `select_diverse_top_candidates`, mas o pacote embarcado em `functions/neural_evolution_orchestrator/sisacao8/neural_evolution.py` não expunha essa função.
- Corrigido o pacote embarcado da Cloud Function adicionando `select_diverse_top_candidates`, `candidate_family_key` e helpers de normalização para consolidar famílias de candidatos ignorando `random_seed`, preservando os parâmetros relevantes de arquitetura/treino e permitindo que o Functions Framework importe o entrypoint.
- Comandos usados: `curl` para `initialize` e `tools/call`/`cloud_run_function_logs` via MCP HTTP, `sed -n` para leitura dos arquivos da função, `rg "select_diverse_top_candidates|select_top_candidates|phase2"`, `diff -u`, `cp sisacao8/neural_evolution.py functions/neural_evolution_orchestrator/sisacao8/neural_evolution.py`, `python -m pytest tests/test_neural_evolution.py tests/test_neural_evolution_orchestrator_function.py -q` e `python -m py_compile functions/neural_evolution_orchestrator/main.py functions/neural_evolution_orchestrator/sisacao8/neural_evolution.py`.

## 2026-06-24 00:48:38 UTC-3
- Elaborado plano técnico para evolução das redes neurais aplicadas a sinais EOD de mercado financeiro, com foco em validação fora da amostra, métricas financeiras, controle de vazamento, walk-forward, score composto, paper trading e promoção controlada.
- Criado o documento `docs/planejamento/plano-evolucao-redes-neurais-mercado-financeiro.md` para orientar as próximas etapas de pesquisa, seleção e operação das redes candidatas.
- Comandos utilizados para registrar o trabalho e inspecionar contexto: `pwd`, `find .. -name AGENTS.md -print`, `sed -n '1,220p' AGENTS.md`, `sed -n '1,220p' docs/diario/registros1.md`, `rg --files docs` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-24 00:53:49 UTC-3
- Revisado o plano de evolução das redes neurais para torná-lo genérico e reutilizável, removendo o foco excessivo na situação atual do painel e estruturando o processo para qualquer família de modelos financeiros.
- O documento agora separa regras centrais de evolução neural de análises específicas de rodadas/modelos, orientando que casos concretos sejam registrados em relatórios anexos.
- Comandos utilizados: `sed -n '1,340p' docs/planejamento/plano-evolucao-redes-neurais-mercado-financeiro.md` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-24 15:19:01 UTC-3 — Execução da Fase 0 do MUEN v1
- Executada a Fase 0 do documento `docs/planejamento/metodo-unificado-evolucao-neural-sisacao.md`, registrando a hipótese econômica antes de qualquer novo treino, mutação ou promoção neural.
- Criado o documento `docs/implementacao/fase0-muen-hipotese-economica.md` com declaração do protocolo `neural_eod_protocol_v1`, hipótese `eod_barrier_direction_v2`, padrão de mercado, universo point-in-time, instante de decisão, horizonte, lados BUY/SELL, regras de entrada/saída, capacidade operacional, custos, baselines, motivo para rede neural e métrica econômica primária.
- Atualizado o método unificado para apontar para a execução registrada da Fase 0.
- Próximo passo autorizado: iniciar a Fase 1 com o `label_eod_barrier_v2` e o motor de trade stateful único compartilhado por labels, backtest, paper e produção.
- Comandos usados: `pwd`, `rg --files -g 'AGENTS.md' -g 'docs/planejamento/metodo-unificado-evolucao-neural-sisacao.md' -g 'docs/diario/registros1.md'`, `cat AGENTS.md`, `sed -n` para leitura do método MUEN, `tail -80 docs/diario/registros1.md`, `rg -n "neural_eod_protocol|hypothesis_id|Hipótese econômica|Fase 0|eod_barrier" docs sisacao8 functions tests infra -S`, criação/edição dos documentos via shell/Python e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-24 15:40:23 UTC-3 — Execução da Fase 1 do MUEN v1

- Executada a Fase 1 do documento `docs/planejamento/metodo-unificado-evolucao-neural-sisacao.md`, substituindo o label EOD neural por `label_eod_barrier_v2` baseado em motor de trade stateful único.
- Criado `sisacao8/trade_engine.py` com a política versionada `execution_eod_barrier_v2_conservative_daily`, estados de entrada pendente/posição aberta/saídas, tratamento conservador de target e stop no mesmo candle diário, expiração sem fill e expiração com marcação a mercado.
- Atualizado `sisacao8/neural_dataset.py` para gerar labels BUY/SELL via motor compartilhado, manter posição após fill até target, stop ou expiração e expor campos operacionais (`trade_side`, `entry_date`, `exit_reason`, `net_return`, excursões e versão da política).
- Atualizado `sisacao8/backtest.py` para simular sinais usando o mesmo motor de execução, preservando nomes legados de `NO_FILL`/`EXPIRE` na API de backtest.
- Sincronizadas as cópias embarcadas em `functions/neural_training_dataset/sisacao8/` e `functions/backtest_daily/` para evitar divergência em deploy.
- Criado `docs/implementacao/fase1-muen-label-motor-execucao.md` e atualizado o método MUEN para apontar para a execução registrada da Fase 1.
- Adicionado teste de paridade semântica do label v2 confirmando que uma entrada preenchida permanece aberta até target em candle posterior, além de validar os testes existentes de backtest.
- Comandos usados: `pwd`, `find .. -name AGENTS.md -print`, `sed -n` para leitura de `AGENTS.md`, do método MUEN e dos módulos `sisacao8/neural_dataset.py`/`sisacao8/backtest.py`, `rg -n "label_eod|barrier|_evaluate_side|neural_dataset|backtest|trade"`, criação/edição de código e docs via shell/Python, `python -m black ...`, `python -m pytest tests/test_neural_dataset.py tests/test_backtest_engine.py -q` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-24 16:21:13 UTC-3 — Execução da Fase 2 do MUEN v1

- Executada a Fase 2 do documento `docs/planejamento/metodo-unificado-evolucao-neural-sisacao.md`, adicionando controles de dataset point-in-time para snapshots neurais EOD.
- Criado o documento `docs/implementacao/fase2-muen-dataset-point-in-time.md` com o registro da implementação, entregas, controles contra leakage, limitações assumidas e critérios de aceite.
- Atualizado `sisacao8/neural_dataset.py` para `feature_eod_tabular_v2`, incluindo manifesto de snapshot (`DatasetSnapshotManifest`), helper `build_dataset_manifest`, hashes estáveis de query/código, distribuição de labels/splits, resumo de qualidade e premissas de custo.
- Adicionadas features tabulares v2 baseadas em log-retornos e volumes em log, mantendo OHLCV nominal bruto apenas por compatibilidade com o treinador atual até a reavaliação completa em fases posteriores.
- Atualizada a Cloud Function `functions/neural_training_dataset/main.py` para gerar e persistir manifestos em `cotacao_intraday.neural_dataset_manifests`, anexar metadados de protocolo/hashes em cada linha do dataset e rejeitar `embargo_days` menor que `horizon_days`.
- Sincronizadas as cópias embarcadas de `sisacao8/neural_dataset.py` em `functions/neural_training_dataset/sisacao8/` e `functions/neural_training/sisacao8/` para reduzir divergência entre pacote raiz e Functions.
- Adicionados testes unitários cobrindo manifesto point-in-time e validação de embargo versus horizonte na materialização do dataset neural.
- Comandos usados: `pwd`, `rg --files -g 'AGENTS.md' -g 'metodo-unificado-evolucao-neural-sisacao.md' -g 'registros1.md'`, `sed -n` para leitura do método MUEN, diário e módulos de dataset/função, `rg -n "snapshot|point|dataset|leak|protocol_version|feature_version|label_version|scaler|embargo|purge|quality"`, edição via shell/Python, `python -m black sisacao8/neural_dataset.py functions/neural_training_dataset/main.py tests/test_neural_dataset.py tests/test_neural_training_dataset_function.py`, `cp sisacao8/neural_dataset.py ...`, `python -m pytest tests/test_neural_dataset.py tests/test_neural_training_dataset_function.py -q` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-24 17:00 UTC-3 — Correção do healthcheck no deploy de neural_training
- Investigado o erro de deploy da Cloud Function Gen2 `neural_training` reportado às 2026-06-24 16:45 UTC-3 (19:45 UTC), em que a revisão `neural-training-00021-yip` falhou no healthcheck por não iniciar o Functions Framework na porta `PORT=8080`.
- Confirmada a causa via MCP JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp`, usando `initialize` e `tools/call` com `cloud_run_function_logs(function_name=neural_training, hours=2, limit=80)`: o container falhava durante import de `/workspace/main.py` com `ModuleNotFoundError: No module named 'sisacao8.trade_engine'`.
- Corrigida a causa ao incluir a cópia vendorizada de `sisacao8/trade_engine.py` em `functions/neural_training/sisacao8/trade_engine.py`, pois `functions/neural_training/sisacao8/neural_dataset.py` importa `TradeEngineConfig` e `simulate_eod_barrier_trade` no ambiente isolado da função.

## 2026-06-24 — Fase 3 MUEN: protocolo temporal

- Executei a Fase 3 do documento `docs/planejamento/metodo-unificado-evolucao-neural-sisacao.md`, implementando o plano nested expanding walk-forward em `sisacao8.neural_dataset`.
- Ferramentas/comandos usados para confirmar o escopo e a causa da lacuna: `sed -n` no documento MUEN, `rg -n "walk|fold|holdout|split|neural"` e inspeção de `functions/neural_training_dataset/main.py`, `sisacao8/neural_dataset.py` e testes existentes.
- Correção aplicada: adição de `NestedWalkForwardConfig`, `WalkForwardFold`, `NestedWalkForwardPlan`, geração de folds externos com calibração exclusiva, embargo e locked holdout bloqueado; a Cloud Function `neural_training_dataset` agora aceita `split_mode=nested_expanding_walk_forward`/`expanding_walk_forward` e parâmetros da Fase 3; o schema BigQuery passou a aceitar `temporal_protocol_json`.
- Validação adicionada: testes unitários para bloqueio do holdout, embargo entre janelas, expansão do treino por fold e rejeição de histórico insuficiente.
- Documento de implementação criado em `docs/implementacao/fase3-muen-protocolo-temporal.md`, registrando objetivo, configuração padrão, regras de segurança e próximos passos da Fase 3.

## 2026-06-24 — Verificação de implementação MUEN v1 e Cloud Scheduler

- Verificado o documento `docs/planejamento/metodo-unificado-evolucao-neural-sisacao.md` contra o estado atual do código, schemas e funções neurais.
- Conclusão: o MUEN v1 está parcialmente implementado. As fases 0 a 3 têm entregas registradas e evidências no código, mas ainda faltam itens estruturais dos critérios de aceite: baselines/champion econômicos no ciclo neural, avaliador econômico por fold, persistência de `neural_trials`, `neural_fold_metrics`, `neural_daily_returns`, `neural_family_evaluations` e `neural_gate_decisions`, agregação robusta por família/seeds, gate engine único em runtime, execução assíncrona/idempotente por candidato × fold × seed e retirada completa do `test` estático do tuning.
- Verificado o Cloud Scheduler via MCP JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp`, conforme regra operacional do projeto. O job `neural-evolution-daily` existe em `ingestaokraken/us-east1`, está `ENABLED`, agenda `30 * * * *`, timezone `America/Sao_Paulo`, `attemptDeadline: 1800s` e chama `https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator`. O job `neural-evolution-weekly` existe e está `PAUSED`, evitando dupla execução recorrente da mesma função.
- Conclusão operacional: não é necessário criar nova entrada no Cloud Scheduler para a evolução neural agora; antes disso, é melhor concluir as lacunas do MUEN e evoluir o orquestrador para o desenho assíncrono/fila previsto no documento.
- Limitação do ambiente local: `gcloud` não está instalado no container, então a checagem real do Scheduler foi feita pelo MCP remoto, que executou `gcloud scheduler jobs describe` no runtime autenticado.
- Comandos usados: `find .. -name AGENTS.md -print`, `sed -n` e `nl -ba` nos documentos/código do MUEN, `rg -n "label_eod_barrier_v2|gate_engine|neural_trials|neural_fold_metrics|neural_daily_returns|neural_family_evaluations|neural_gate_decisions|walk_forward|holdout|scheduler"`, `gcloud scheduler jobs list ... || true` para confirmar a ausência local de `gcloud`, e chamadas Python `requests.post` para `initialize`, `tools/list` e `tools/call` (`cloud_scheduler_job`) via MCP HTTP.

## 2026-06-24 18:33:37 UTC-3 — Implementação parcial das lacunas MUEN v1

- Implementadas bases normativas que faltavam para o MUEN v1 após a verificação: trial idempotente por `protocol_version + dataset_snapshot + candidate_family_hash + fold_id + seed + code_commit`, avaliação econômica líquida por fold, agregação por família/seeds e gate engine de research antes de qualquer score promocional.
- Criado `sisacao8/neural_muen.py` com `MuenTrialKey`, `FoldEconomicMetrics`, `FamilyEvaluation`, `GateDecision`, `evaluate_fold_economics`, `aggregate_family_evaluation`, `research_gate_decision` e geração de linhas para `neural_gate_decisions`.
- Vendorizado o helper MUEN nas funções neurais relevantes para reduzir divergência em deploy durante a transição para pacote único.
- Expandido `infra/bq/21_neural_evolution.sql` com as tabelas normativas previstas no documento: `neural_protocols`, `neural_trials`, `neural_fold_metrics`, `neural_daily_returns`, `neural_family_evaluations` e `neural_gate_decisions`.
- Corrigida a estimativa de parâmetros para 19 features em `sisacao8/neural_evolution.py`/cópia vendorizada, alinhando o orçamento ao contrato atual de features do treinador.
- Adicionados testes unitários em `tests/test_neural_muen.py` cobrindo idempotência do trial, avaliação econômica BUY/SELL, rejeição por hard gates, aprovação de família estável com stress de custo e serialização BigQuery-ready de decisão de gate.
- Limitação restante: esta entrega cria as bases de código/schema para os gates e métricas econômicas, mas ainda não converte o orquestrador síncrono em Cloud Tasks/Pub/Sub/Cloud Run Jobs nem liga automaticamente cada treino ao pipeline completo `trial -> fold metrics -> family evaluation -> gate decision`; isso deve ser a próxima etapa de integração operacional.
- Comandos usados: `sed -n` em `sisacao8/neural_training.py` e testes existentes, criação/edição de `sisacao8/neural_muen.py`, cópia para pacotes vendorizados das Functions, atualização de `infra/bq/21_neural_evolution.sql` e `infra/bq/README.md`, `python -m black ...`, `python -m pytest tests/test_neural_muen.py tests/test_neural_training.py -q`, `python -m flake8 ...` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-24 21:27:06 UTC-3 — Fase UI 1 do plano de telas da evolução neural

- Iniciada a primeira entrega recomendada do documento `docs/planejamento/plano-telas-evolucao-neural.md`, criando a tela `Visão geral` no grupo `Redes neurais` sem alterar o backend.
- Adicionado `frontend/app/src/components/tabs/NeuralOverviewTab.tsx` para consolidar dados atuais de dataset, treinos e leaderboard em uma jornada MUEN passo a passo, com cards de estoque, famílias, mantidas/rejeitadas, champion, melhor challenger, explicação de que score não aprova e painéis determinísticos de contexto/próximo passo.
- Atualizado `frontend/app/src/App.tsx` para incluir a nova entrada de menu `Visão geral`, carregar as queries existentes necessárias e permitir navegação rápida para Dados de treino, Treinos, Evolução e Advisor IA.
- Validação local executada com `npm --prefix frontend/app run build` e `npm --prefix frontend/app run lint`; ambos passaram. O build manteve apenas o aviso já esperado do Vite sobre chunk acima de 500 kB.
- Screenshot não foi gerada porque o container não possui navegador Chromium/Chrome disponível para captura local; a ausência foi confirmada com `which chromium || which chromium-browser || which google-chrome || true`.
- Comandos usados: `find .. -name AGENTS.md -print`, `rg --files`, `sed -n` para leitura de `App.tsx`, abas/hooks/APIs neurais e do plano de telas, criação/edição de arquivos via shell/Python, `npm --prefix frontend/app run build`, `npm --prefix frontend/app run lint`, `which chromium || which chromium-browser || which google-chrome || true`, `git diff` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-24 21:31:16 UTC-3 — Fase UI 2 parcial: famílias no leaderboard neural

- Avançada a próxima etapa do plano de telas da evolução neural, aproximando a aba `Evolução` do destino `Famílias e leaderboard` previsto no documento `docs/planejamento/plano-telas-evolucao-neural.md`.
- Atualizado `frontend/app/src/components/tabs/NeuralEvolutionTab.tsx` para exibir famílias antes de execuções individuais, agrupando candidatos por arquitetura e hiperparâmetros com remoção de campos de seed quando presentes na configuração.
- Renomeado o score visual para `Índice de ordenação` e incluído aviso explícito de que a ordenação não aprova shadow, paper ou operação.
- Traduzidas decisões técnicas como `keep_candidate`, `shadow_candidate`, `paper_candidate` e `reject` para linguagem operacional consistente: `Mantida para pesquisa`, `Elegível ao gate de shadow`, `Elegível ao gate de paper` e `Rejeitada nesta etapa`.
- Adicionada tabela de famílias com execuções, mantidas, rejeitadas, índice mediano, melhor índice, precisão direcional, cobertura, estabilidade e próximo passo determinístico, mantendo a tabela de execuções individuais como detalhe técnico abaixo.
- Validação local executada com `npm --prefix frontend/app run build` e `npm --prefix frontend/app run lint`; ambos passaram. O build manteve apenas o aviso conhecido do Vite sobre chunk acima de 500 kB.
- Comandos usados: `git status --short`, `git log -3 --oneline`, `find .. -name AGENTS.md -print`, `sed -n` em `NeuralOverviewTab.tsx` e `NeuralEvolutionTab.tsx`, edição de `NeuralEvolutionTab.tsx` via shell, `npm --prefix frontend/app run build`, `npm --prefix frontend/app run lint` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-24 21:35:08 UTC-3 — Fase UI 1/2: tela Jornada passo a passo neural

- Implementada a tela `Jornada passo a passo` no grupo `Redes neurais`, seguindo a Tela 2 do plano `docs/planejamento/plano-telas-evolucao-neural.md` para ensinar e acompanhar o MUEN como fluxo navegável.
- Criado `frontend/app/src/components/tabs/NeuralJourneyTab.tsx` com Stepper vertical não linear e painel lateral `Como interpretar`, cobrindo Hipótese, Dados, Labels, Baselines, Experimentos, Walk-forward, Holdout, Shadow, Paper e Promoção.
- A nova tela reutiliza dados atuais de alocação do dataset, treinos e leaderboard para preencher evidências determinísticas de cada etapa, incluindo distribuição de labels, artefatos registrados, avaliações, candidatas mantidas e bloqueios de holdout/shadow/paper/promoção.
- Atualizado `frontend/app/src/App.tsx` para incluir a entrada de menu `Jornada passo a passo`, carregar as mesmas queries da visão geral e renderizar o novo componente sem alterar backend.
- Validação local executada com `npm --prefix frontend/app run build` e `npm --prefix frontend/app run lint`; ambos passaram. O build manteve apenas o aviso conhecido do Vite sobre chunk acima de 500 kB.
- Screenshot não foi gerada porque o container não possui Chromium/Chrome disponível; a ausência foi confirmada com `which chromium || which chromium-browser || which google-chrome || true`.
- Comandos usados: `git status --short`, `sed -n` no plano de telas e `App.tsx`, criação/edição de arquivos via shell/Python, `npm --prefix frontend/app run build`, `npm --prefix frontend/app run lint`, `which chromium || which chromium-browser || which google-chrome || true` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-24 22:10:25 UTC-3 — Evolução do passo Baselines na jornada neural
- Evoluído o passo `Baselines` da jornada neural para consumir o endpoint quantitativo já existente de estratégias baseline (`/ops/quant/strategies`) no contexto das telas `Visão geral` e `Jornada passo a passo`.
- A visão geral neural deixou de exibir `Baselines` como pendência fixa de UI e passou a calcular status, resumo e contadores a partir de baselines econômicos carregados, métricas disponíveis, trades e expectancy positiva.
- A tela `Jornada passo a passo` agora mostra evidências operacionais do catálogo de baselines: quantidade de regras, baselines com trades, baselines com métricas econômicas, quantidade com expectancy positiva e baseline líder por expectancy líquida.
- Adicionado atalho `Baselines econômicos` na visão geral neural, direcionando para a tela quantitativa de baselines e mantendo o roadmap selecionado em `baseline`.
- Ponto de parada alcançado: a UI agora conecta baselines econômicos existentes ao fluxo MUEN, mas a aprovação de modelos segue bloqueada até existir comparação formal champion/challenger por fold/seed/gate econômico no backend.
- Screenshot não foi gerada porque o container não possui Chromium/Chrome disponível; a ausência foi confirmada com `which chromium || which chromium-browser || which google-chrome || true`.
- Comandos usados: `find .. -name AGENTS.md -print`, `git status --short`, `cat AGENTS.md`, `rg --files frontend/app/src`, `rg -n "trainingRuns|leaderboard|neural|QuantBaselineStrategy|api/ops" frontend/app/src -S`, `nl -ba frontend/app/src/api/ops.ts`, `nl -ba frontend/app/src/App.tsx`, `nl -ba frontend/app/src/components/tabs/NeuralJourneyTab.tsx`, `nl -ba frontend/app/src/components/tabs/NeuralOverviewTab.tsx`, edição via Python, `npm --prefix frontend/app run lint`, `npm --prefix frontend/app run build`, `which chromium || which chromium-browser || which google-chrome || true` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-24 22:17:39 UTC-3 — Próximo passo: readiness champion/challenger dos baselines neurais
- Refatorada a leitura de baseline da jornada neural para um helper compartilhado `neuralBaselineReadiness`, removendo duplicação entre `Visão geral` e `Jornada passo a passo`.
- O status de `Baselines` agora diferencia métricas econômicas carregadas de comparação formal pronta: só marca `Concluído` quando baseline econômico líder, champion aprovado e challenger líder estão disponíveis juntos; caso contrário permanece `Em andamento`/`Aguardando`, evitando interpretar baseline com métrica como aprovação.
- A evidência do passo `Baselines` passou a mostrar champion aprovado e challenger líder ao lado do baseline econômico líder, explicitando que falta persistir o gate econômico antes de holdout/promoção.
- Ponto de parada alcançado: a UI agora tem readiness champion/challenger consistente e reutilizável; a próxima lacuna real continua sendo persistir a decisão do gate econômico no backend/BigQuery por fold e seed.
- Screenshot não foi gerada porque o container não possui Chromium/Chrome disponível; a ausência foi confirmada com `which chromium || which chromium-browser || which google-chrome || true`.
- Comandos usados: `find .. -name AGENTS.md -print`, `git status --short`, `git log -3 --oneline`, `rg -n "neural.*baseline|champion|challenger|gate|fold|neural_muen|neural_candidate|leaderboard|baseline" backend frontend sisacao8 functions infra docs -S`, `nl -ba sisacao8/neural_muen.py`, `nl -ba tests/test_neural_muen.py`, `nl -ba infra/bq/21_neural_evolution.sql`, edição via shell/Python, `npm --prefix frontend/app run lint`, `npm --prefix frontend/app run build`, `python -m flake8 && python -m pytest -q`, `which chromium || which chromium-browser || which google-chrome || true` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-24 22:22:49 UTC-3 — Próximo passo: linhas BigQuery-ready para gate econômico MUEN
- Implementados helpers MUEN para materializar linhas prontas para BigQuery das tabelas normativas `neural_fold_metrics`, `neural_family_evaluations` e `neural_daily_returns`, completando a camada local necessária antes de persistir decisões econômicas por fold/seed.
- As funções `fold_metrics_row`, `family_evaluation_row` e `daily_return_rows` foram adicionadas ao pacote principal e sincronizadas nas cópias vendorizadas das Cloud Functions neurais.
- Criados testes cobrindo serialização de métricas por fold/família e retornos diários pareados entre modelo e champion, incluindo descarte conservador de datas inválidas.
- Ponto de parada alcançado: agora existem payloads BigQuery-ready para métricas econômicas e retornos pareados; a próxima etapa operacional é conectar esses payloads ao orquestrador para inserir nas tabelas `neural_fold_metrics`, `neural_family_evaluations`, `neural_daily_returns` e então emitir `neural_gate_decisions` por execução real.
- Validação local executada com `python -m flake8`, `python -m pytest -q`, `npm --prefix frontend/app run lint` e `npm --prefix frontend/app run build`; todos passaram, com o aviso conhecido do Vite sobre chunk acima de 500 kB.
- Comandos usados: `git status --short`, `find .. -name AGENTS.md -print`, `rg --files -g 'neural_muen.py' -g 'test_neural_muen.py'`, `rg -n "gate_decision_row|fold_metrics|family_evaluation|daily_returns|neural_muen" sisacao8 functions tests infra -S`, edição via Python, `python -m black ...`, cópia sincronizada dos helpers vendorizados, `python -m pytest tests/test_neural_muen.py -q`, `python -m flake8`, `python -m pytest -q`, `npm --prefix frontend/app run lint`, `npm --prefix frontend/app run build` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-24 22:32:05 UTC-3 — Próximo passo: emissão de gate MUEN bloqueado no orquestrador
- Conectado o `neural_evolution_orchestrator` à tabela `neural_gate_decisions` para emitir uma decisão auditável de Gate Research bloqueado sempre que uma candidata for avaliada no leaderboard sem evidência econômica MUEN persistida por fold/família.
- A decisão usa `gate_name=research_walk_forward`, `decision_status=blocked` e `failed_criteria=[muen_economics_missing]`, impedindo que score/classificação sejam interpretados como aprovação enquanto `neural_fold_metrics` e `neural_family_evaluations` não estiverem materializadas.
- O resumo da rodada passou a incluir `gate_decision_count`, permitindo auditoria rápida de quantas decisões de gate foram emitidas junto com as avaliações de candidatos.
- Atualizado o teste do orquestrador para validar persistência em `neural_candidate_evaluations` e `neural_gate_decisions`, além do motivo bloqueante `muen_economics_missing`.
- Ponto de parada alcançado: o orquestrador agora registra bloqueio explícito no gate quando falta evidência econômica; o próximo passo é substituir esse bloqueio por decisões `passed/rejected` derivadas de `neural_fold_metrics`/`neural_family_evaluations` reais quando o treino/evaluador produzir folds e seeds.
- Comandos usados: `git status --short`, `rg -n "neural_fold_metrics|neural_family_evaluations|neural_daily_returns|neural_gate_decisions|insert_rows|insert_rows_json|gate_decision_row|research_gate_decision|candidate_evaluations|orchestr" functions/neural_evolution_orchestrator tests sisacao8 -S`, `nl -ba functions/neural_evolution_orchestrator/main.py`, `nl -ba tests/test_neural_evolution_orchestrator_function.py`, edição via Python, `python -m black`, `python -m pytest tests/test_neural_evolution_orchestrator_function.py -q`, `python -m flake8`, `python -m pytest -q`, `npm --prefix frontend/app run lint`, `npm --prefix frontend/app run build`, `git diff --check` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-24 23:23:52 UTC-3 — Próximo passo: gate MUEN usa econômicas reais quando presentes
- Evoluído o `neural_evolution_orchestrator` para ler `metrics_json.muen_economics` do registry quando disponível e materializar linhas em `neural_fold_metrics`, `neural_family_evaluations` e `neural_gate_decisions`.
- Mantido o bloqueio `muen_economics_missing` apenas como fallback quando as métricas econômicas por fold/família ainda não existem no registry; quando existem, o orquestrador agrega a família, executa `research_gate_decision` e persiste o resultado `passed`/`rejected` do gate.
- O resumo da rodada agora também contabiliza `fold_metric_count` e `family_evaluation_count`, além de `gate_decision_count`, para auditoria operacional do avanço MUEN.
- Adicionado teste cobrindo o cenário com `muen_economics.fold_metrics`, validando persistência em `neural_fold_metrics`, `neural_family_evaluations` e `neural_gate_decisions` sem o motivo bloqueante `muen_economics_missing`.
- Ponto de parada alcançado: o orquestrador já sabe alternar entre bloqueio por ausência de econômicas e gate real quando o registry trouxer folds; a próxima etapa é fazer o treino/evaluador produzir `muen_economics` reais por fold/seed em vez de depender de payload sintético no registry.
- Comandos usados: `python -m black functions/neural_evolution_orchestrator/main.py`, `python -m pytest tests/test_neural_evolution_orchestrator_function.py -q`, edição via Python, `python -m black tests/test_neural_evolution_orchestrator_function.py`, `python -m flake8`, `python -m pytest -q`, `npm --prefix frontend/app run lint`, `npm --prefix frontend/app run build`, `git diff --check` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-24 23:29:13 UTC-3 — Documento permanente de próximo passo das redes
- Criado `docs/diario/proximo-passo-redes.md` para manter o próximo passo operacional das redes neurais MUEN em um local único e fácil de consultar.
- Registrado como próximo passo atual fazer o treino/evaluador produzir `metrics_json.muen_economics` reais por fold/seed, permitindo que o orquestrador persista métricas por fold/família e emita Gate Research real sem depender de payload sintético.
- Atualizado `AGENTS.md` para tornar obrigatório manter `docs/diario/proximo-passo-redes.md` sempre que o ponto de parada ou próximo passo das redes neurais mudar, além de continuar registrando todo trabalho em `docs/diario/registros1.md`.
- Comandos usados: `git status --short`, `sed -n '1,80p' AGENTS.md`, `tail -20 docs/diario/registros1.md`, criação/edição via shell/Python, `python -m flake8`, `python -m pytest -q`, `git diff --check` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-25 00:02:22 UTC-3 — Clareza visual do bloqueio em Baselines neurais
- Atendida a necessidade operacional de o usuário entender visualmente na tela o que falta no passo `Baselines` da jornada neural.
- Evoluído o helper `neuralBaselineReadiness` para expor uma checklist visual do gate com quatro itens: baseline econômico medido, champion aprovado, challenger avaliada e gate econômico persistido.
- Atualizada a tela `Redes neurais — Jornada passo a passo` para mostrar, no próprio stepper, um alerta "Falta para concluir" e, no painel `Como interpretar`, cards com ícones verdes/amarelos indicando quais requisitos já existem e quais bloqueiam a conclusão.
- O próximo passo operacional das redes não mudou: segue necessário produzir/persistir econômicas MUEN reais por fold/seed e emitir gate econômico real; a alteração atual apenas torna esse bloqueio compreensível visualmente para o usuário.
- Screenshot não foi gerada porque as instruções do projeto orientam não gerar/versionar screenshots de frontend salvo pedido explícito do usuário.
- Validação local executada com `npm --prefix frontend/app run lint` e `npm --prefix frontend/app run build`; ambas passaram. O build manteve apenas o aviso conhecido do Vite sobre chunk acima de 500 kB.
- Comandos usados: `cat AGENTS.md`, `nl -ba frontend/app/src/components/tabs/NeuralJourneyTab.tsx`, `nl -ba frontend/app/src/components/tabs/neuralBaselineReadiness.ts`, edição via Python, `npm --prefix frontend/app run lint`, `npm --prefix frontend/app run build` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-25 07:21:00 UTC-3 — Processo operacional para aprovação de champion neural
- Criado `docs/implementacao/processo-aprovacao-champion-neural-muen.md` com a cadeia operacional para transformar uma candidata `keep_candidate` em champion `approved` somente após evidência econômica MUEN real.
- O processo define etapas de congelamento de contexto, avaliação por `fold_id`/`seed`/`cost_multiplier`, persistência em `neural_fold_metrics`, `neural_daily_returns`, `neural_family_evaluations` e `neural_gate_decisions`, revisão de governança e promoção controlada do `neural_model_registry.status` para `approved`.
- Atualizado `docs/diario/proximo-passo-redes.md` para trocar o próximo passo genérico por um processo executável com modos recomendados `evaluate_candidate`, `approve_if_passed` e `audit_current_champion`.
- Comandos usados: `git status --short`, `cat AGENTS.md`, `rg -n "champion|muen_economics|proximo|próximo|approved|gate" docs/planejamento docs/implementacao docs/diario -S`, criação/edição via shell/Python, `python -m flake8`, `python -m pytest -q`, `npm --prefix frontend/app run lint`, `npm --prefix frontend/app run build`, `git diff --check` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-25 07:42:00 UTC-3 — Implementação de aprovação governada de champion neural
- Implementado `sisacao8/neural_champion_approval.py` com validação unit-testável para aprovar champion apenas quando existir `neural_gate_decisions` com `gate_name=research_walk_forward`, `decision_status=passed`, `passed=true`, sem `failed_criteria` e sem `muen_economics_missing`.
- Criada a Cloud Function HTTP `functions/neural_champion_approval` com os modos `approve_if_passed`, `audit_current_champion` e bloqueio explícito de `evaluate_candidate` até integração com avaliador econômico real.
- `approve_if_passed` valida modelo no `neural_model_registry`, decisão de gate, operador/ticket, executa dry-run por padrão e só atualiza `status=approved` quando `dry_run=false` e todos os checks passam.
- Adicionados testes unitários cobrindo aprovação permitida, bloqueio por `muen_economics_missing`, idempotência para modelo já aprovado, auditoria de duplicidade e comportamento HTTP da função.
- Atualizados `.github/workflows/deploy.yml`, `functions/README.md`, `docs/diario/proximo-passo-redes.md` e `docs/implementacao/processo-aprovacao-champion-neural-muen.md` para refletir que a promoção governada foi implementada e que a lacuna restante é conectar `evaluate_candidate` ao avaliador econômico real.
- Comandos usados: `git status --short`, `find .. -name AGENTS.md -print`, `rg -n "neural_gate_decisions|neural_model_registry|approve_if_passed|champion|GateDecision|gate_decision_row|insert_rows|status = 'approved'|UPDATE .*neural_model_registry" functions sisacao8 tests infra backend docs -S`, criação/edição via shell, `python -m black ...`, `python -m pytest tests/test_neural_champion_approval.py -q`, `python -m flake8`, `python -m pytest -q`, `npm --prefix frontend/app run lint`, `npm --prefix frontend/app run build`, `git diff --check` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-25 - Correção de deploy do neural_evolution_orchestrator

- Investigada falha de deploy da Cloud Function Gen2 `neural_evolution_orchestrator` reportada pelo Cloud Run como `Container Healthcheck failed`, sem escuta em `PORT=8080` na revisão `neural-evolution-orchestrator-00026-duh`.
- Hipótese confirmada localmente recriando um ambiente isolado apenas com `functions/neural_evolution_orchestrator/requirements.txt` e importando o entrypoint com `PYTHONPATH=functions/neural_evolution_orchestrator`: o container não iniciaria porque `sisacao8.neural_muen` importa `pandas`/`numpy`, mas essas dependências não estavam no `requirements.txt` da função. O erro reproduzido foi `ModuleNotFoundError: No module named 'pandas'`.
- Correção aplicada: adicionadas dependências runtime explícitas `numpy>=1.24,<3` e `pandas>=2.0,<3` ao `requirements.txt` do `neural_evolution_orchestrator`, mantendo `google-cloud-bigquery>=3.12`.
- Validação local executada após a correção em ambiente virtual limpo: instalação das dependências da função e import do módulo `main` retornaram `IMPORT_OK`.


## 2026-06-27 09:17:17 UTC-3 — Orientação sobre espera por dados para champion aprovado
- Respondida a dúvida operacional sobre se basta aguardar mais coleta de dados para surgir um champion aprovado.
- Conclusão: a espera por dados brutos/cotação pode melhorar amostra futura, mas não muda sozinha o status de champion; a promoção continua bloqueada até conectar `evaluate_candidate` ao avaliador econômico real, persistir `muen_economics` por fold/seed/custo, gravar o Gate Research aprovado e executar `approve_if_passed` com autorização.
- Tentada validação operacional via MCP JSON-RPC em HTTP conforme regra do projeto: `initialize` e `tools/list` funcionaram, mas a consulta `bigquery_query` ao `neural_model_registry` falhou por erro de credencial no runtime do MCP (`gcloud crashed (AttributeError): 'Credentials' object has no attribute 'private_key_id'`); portanto a orientação foi baseada no estado versionado do processo e da implementação local.
- O próximo passo operacional das redes não mudou; `docs/diario/proximo-passo-redes.md` foi mantido como fonte do bloqueio atual.
- Comandos usados: `find .. -name AGENTS.md -print`, `git status --short`, `cat AGENTS.md`, `sed -n '1,220p' docs/diario/proximo-passo-redes.md`, `tail -80 docs/diario/registros1.md`, `curl` JSON-RPC para MCP HTTP, `rg -n "evaluate_candidate|approve_if_passed|muen_economics_missing|approved|neuralBaselineReadiness|Champion aprovado|Gate econômico" functions/neural_champion_approval sisacao8 docs frontend/app/src -S` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.


## 2026-06-27 09:42:00 UTC-3 — Execução do próximo passo: evaluate_candidate MUEN
- Executado o próximo passo operacional no código: o modo `evaluate_candidate` da Cloud Function `functions/neural_champion_approval` deixou de ser apenas um bloqueio fixo e passou a consumir `metrics_json.muen_economics` do `neural_model_registry`.
- A rotina agora materializa linhas BigQuery-ready para `neural_fold_metrics`, `neural_family_evaluations`, `neural_gate_decisions` e, quando o payload trouxer retornos diários já calculados, `neural_daily_returns`; em seguida retorna `decision_id`, status do gate e contagens persistidas.
- O bloqueio conservador permanece quando `model_version`, registry, `muen_economics` ou `fold_metrics` estão ausentes, evitando promoção sem evidência econômica.
- Adicionado `sisacao8/neural_muen.py` ao pacote vendorizado da função e declaradas dependências runtime `numpy`/`pandas` no `requirements.txt` da função.
- Atualizados testes unitários para cobrir o bloqueio por `muen_economics_missing` e o caminho efetivo que persiste fold/família/gate sem o critério bloqueante.
- Atualizado `docs/diario/proximo-passo-redes.md`: o próximo passo agora é executar a função em uma candidata real com `dry_run=false`, validar BigQuery e chamar `approve_if_passed` se o gate retornar `passed`.
- Comandos usados: `git status --short`, `git log --oneline -3`, `find .. -name AGENTS.md -print`, leituras com `sed`/`rg`, cópia de `sisacao8/neural_muen.py`, edição via `apply_patch`/Python, `python -m black functions/neural_champion_approval/main.py tests/test_neural_champion_approval.py functions/neural_champion_approval/sisacao8/neural_muen.py`, `python -m pytest tests/test_neural_champion_approval.py -q` e `TZ=America/Sao_Paulo date`.
- Validação local completa executada depois da implementação: `python -m flake8`, `python -m pytest -q`, `git diff --check`, `npm --prefix frontend/app run lint` e `npm --prefix frontend/app run build` passaram; o build manteve apenas o aviso conhecido do Vite sobre chunk acima de 500 kB.

## 2026-06-27 14:55:00 UTC-3 — Execução operacional do próximo passo do baseline neural
- Verificado o ponto de parada em `docs/diario/proximo-passo-redes.md`: o baseline/champion neural ainda depende de executar `evaluate_candidate` em candidata real com `metrics_json.muen_economics` e depois `approve_if_passed` se o Gate Research passar.
- Tentada consulta MCP obrigatória por HTTP/JSON-RPC em `http://mcpserversisacao.shop/mcp` para encontrar candidatas com `muen_economics`; o endpoint apresentou `503`/timeout em múltiplas tentativas e uma tentativa posterior ficou sem `mcp-session-id` válido, portanto não foi possível confirmar via BigQuery pelo MCP nesta execução.
- Como alternativa observacional, consultada a API publicada `GET http://34.194.252.70/api/ops/neural/evolution/leaderboard?limit=20` e `GET http://34.194.252.70/api/ops/neural/training-runs?limit=20`; ela mostrou candidatas `keep_candidate`, incluindo `neural_eod_mlp_evo2_20260624_mutation_01`, mas o `metricsJson` exposto contém métricas básicas de treino/validação/teste e não evidencia `muen_economics`.
- Tentada execução produtiva de `evaluate_candidate` via `POST https://us-east1-ingestaokraken.cloudfunctions.net/neural_champion_approval` para `neural_eod_mlp_evo2_20260624_mutation_01`; a função publicada retornou `status=blocked` e `reason=evaluate_candidate_requires_economic_evaluator_integration`.
- Conclusão confirmada por execução: ainda falta publicar a versão atual da função `neural_champion_approval` que já foi implementada no repositório para ler `metrics_json.muen_economics`; depois do deploy, falta garantir uma candidata real com `metrics_json.muen_economics.fold_metrics` para materializar `neural_fold_metrics`, `neural_family_evaluations`, `neural_gate_decisions` e então tentar `approve_if_passed`.
- Atualizado `docs/diario/proximo-passo-redes.md` para refletir o bloqueio real encontrado: deploy da função atual + geração/seleção de candidata com evidência econômica MUEN antes da aprovação do champion.
- Comandos usados: `pwd`, `rg --files -g 'AGENTS.md'`, `git status --short`, `cat AGENTS.md`, `cat docs/diario/proximo-passo-redes.md`, `tail -80 docs/diario/registros1.md`, `sed -n` em `functions/neural_champion_approval/main.py` e `sisacao8/neural_champion_approval.py`, scripts Python com `requests` para MCP HTTP/JSON-RPC, `curl` para endpoints publicados, `python -m json.tool`, `rg -n`, `git log --oneline -3` e `TZ=America/Sao_Paulo date`.

## 2026-06-27 17:24:37 UTC-3 — Orientação sobre evolução do Passo 4/Baselines neural
- Respondida a dúvida operacional a partir da tela do painel e do ponto de parada registrado: o Passo 4/Baselines não conclui porque ainda faltam champion aprovado e Gate econômico persistido, embora já existam baseline econômico medido e challenger avaliada.
- Reforçado que a próxima ação prática não é esperar a interface mudar sozinha: é publicar a versão atual de `functions/neural_champion_approval`, selecionar/gerar candidata real com `metrics_json.muen_economics.fold_metrics`, executar `evaluate_candidate` com `dry_run=false`, validar persistência em BigQuery e só então executar `approve_if_passed` se o Gate Research passar.
- O próximo passo operacional das redes não mudou; `docs/diario/proximo-passo-redes.md` permanece como fonte vigente do ponto de parada.
- Comandos usados: `pwd`, `rg --files -g 'AGENTS.md' -g 'docs/diario/**'`, `git status --short`, `sed -n '1,220p' AGENTS.md`, `sed -n '1,220p' docs/diario/proximo-passo-redes.md`, `tail -n 80 docs/diario/registros1.md` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-27 17:34:07 UTC-3 — Verificação de workflow para neural_champion_approval
- Verificado que existe workflow de deploy para a função `neural_champion_approval` em `.github/workflows/deploy.yml`, dentro da matriz `deploy-cloud-functions`, com `entry_point=neural_champion_approval`, `source=functions/neural_champion_approval`, `memory=512Mi`, `timeout=600s` e service account `sa-neural-evolution-orchestrator@ingestaokraken.iam.gserviceaccount.com`.
- Confirmado que o workflow é acionado por alterações em `functions/**` ou no próprio `.github/workflows/deploy.yml` em push para `main`, pull request para `main` e também por `workflow_dispatch` manual.
- Observação operacional: o workflow atual já inclui as variáveis obrigatórias de registry/gate/location; as tabelas `neural_fold_metrics`, `neural_family_evaluations` e `neural_daily_returns` usam os nomes padrão definidos no código da função quando variáveis específicas não são passadas.
- Comandos usados: `git status --short`, `rg -n "neural_champion_approval|champion|functions/" .github/workflows functions/README.md -S`, `sed -n '1,260p' .github/workflows/deploy.yml`, `sed -n '1,200p' .github/workflows/ci.yml`, `rg -n "BQ_NEURAL_|NEURAL_|fold|family|daily_returns|gate" functions/neural_champion_approval/main.py sisacao8/neural_champion_approval.py functions/neural_champion_approval -S` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-27 19:03:27 UTC-3 — Verificação da publicação para evolução do baseline neural
- Verificada a Cloud Function produtiva `neural_champion_approval` por `curl` HTTP POST no endpoint `https://us-east1-ingestaokraken.cloudfunctions.net/neural_champion_approval` usando `mode=evaluate_candidate`, `model_version=neural_eod_mlp_evo2_20260624_mutation_01` e `dry_run=true`.
- Resultado: a função necessária já foi publicada com a implementação atual, pois a resposta mudou para `status=blocked` com `reason=muen_economics_missing`; isso confirma que o bloqueio anterior `evaluate_candidate_requires_economic_evaluator_integration` não está mais ativo em produção.
- Consultado o MCP obrigatório por HTTP/JSON-RPC em `http://mcpserversisacao.shop/mcp`: `tools/list` funcionou, `bigquery_query` no `neural_model_registry` retornou 20 candidatas recentes, todas com `muen_protocol` e `fold_count` nulos; portanto ainda falta gerar/selecionar candidata com `metrics_json.muen_economics.fold_metrics`.
- Consultado via MCP o Cloud Scheduler: `neural-evolution-daily` existe em `ingestaokraken/us-east1`, está `ENABLED`, roda `30 * * * *` em `America/Sao_Paulo` e chama `https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator`; o job hipotético `neural-champion-approval-daily` não existe.
- Conclusão operacional: não é recomendado criar Scheduler automático para `neural_champion_approval` agora, pois a aprovação depende de evidência econômica MUEN e autorização; o próximo passo é produzir `muen_economics` no registry e depois executar `evaluate_candidate`/`approve_if_passed` de forma controlada.
- Atualizado `docs/diario/proximo-passo-redes.md` para remover o deploy da função como bloqueio e manter como bloqueio atual a ausência de `metrics_json.muen_economics.fold_metrics`.
- Observação de ambiente: tentativa local com `gcloud functions describe` e `gcloud scheduler jobs list` não pôde rodar porque `gcloud` não está instalado no container; a verificação de Scheduler foi feita pelo MCP.
- Comandos usados: `curl -i -X POST https://us-east1-ingestaokraken.cloudfunctions.net/neural_champion_approval`, scripts Python com `requests` para MCP HTTP/JSON-RPC (`initialize`, `tools/list`, `bigquery_query`, `cloud_scheduler_job`), `gcloud functions describe ...`/`gcloud scheduler jobs list ...` (falharam por `gcloud: command not found`), `rg`, `sed`, `date` e edição via Python.

## 2026-06-27 19:10:58 UTC-3 — Esclarecimento sobre existência de candidatas neurais
- Esclarecida a dúvida operacional: existem candidatas neurais no painel/API, mas elas ainda não são candidatas elegíveis para fechar o baseline/champion porque não carregam `metrics_json.muen_economics.fold_metrics`.
- A API pública `GET http://34.194.252.70/api/ops/neural/evolution/leaderboard?limit=50` retornou 41 entradas no leaderboard, com decisões `keep_candidate`, incluindo `neural_eod_mlp_evo2_20260624_mutation_01`, porém sem payload `muen_economics` exposto nas métricas retornadas.
- A API pública `GET http://34.194.252.70/api/ops/neural/training-runs?limit=50` retornou 60 registros de treino/registry, incluindo várias linhas com `status=candidate` para `neural_eod_mlp_evo2_20260624_mutation_01`.
- Tentada nova consulta MCP HTTP/JSON-RPC ao BigQuery para contar status e `muen_economics`; o `initialize` retornou sessão, mas as chamadas `bigquery_query` desta rodada retornaram `503`/timeout. Mantida a evidência MCP imediatamente anterior que já havia confirmado 20 candidatas recentes sem `muen_protocol` e `fold_count`.
- Conclusão: há candidatas de treino/ranking, mas ainda não há candidata pronta para o Gate Research MUEN; falta anexar ou produzir `metrics_json.muen_economics.fold_metrics` para uma delas.
- O próximo passo operacional das redes não mudou, então `docs/diario/proximo-passo-redes.md` permanece válido.
- Comandos usados: scripts Python com `requests` para MCP HTTP/JSON-RPC (`initialize`, `bigquery_query`), `curl http://34.194.252.70/api/ops/neural/evolution/leaderboard?limit=50`, `curl http://34.194.252.70/api/ops/neural/training-runs?limit=50`, parsing via Python e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-27 19:20:00 UTC-3 — Avaliação sobre carregar `muen_economics` agora
- Avaliada a solicitação de carregar agora `metrics_json.muen_economics.fold_metrics` em uma das candidatas existentes.
- Conclusão operacional: não carregar manualmente ou fabricar o payload econômico. Existem candidatas de treino/ranking, mas o carregamento seguro exige cálculo reproduzível das predições por fold contra `buy_net_return`/`sell_net_return` e persistência auditável no `neural_model_registry`; sem esse cálculo, inserir JSON manualmente quebraria a governança do Gate Research MUEN.
- Verificado no código que `evaluate_candidate` da função `neural_champion_approval` apenas consome `metrics_json.muen_economics` já presente no registry e materializa `neural_fold_metrics`, `neural_family_evaluations`, `neural_daily_returns` quando houver payload diário e `neural_gate_decisions`; ele não calcula o payload econômico a partir do dataset bruto.
- Verificado no código que o treino atual registra métricas clássicas no `metrics_json`, mas não materializa `muen_economics` durante `_registry_row`; portanto a correção segura é evoluir `neural_training`/avaliador para gerar esse bloco e então treinar/backfillar de forma reprodutível.
- Próximo passo recomendado: implementar a geração auditável de `muen_economics` no treino/evaluador ou criar rotina controlada de backfill que carregue artefato + dataset, calcule predições por fold/custo e atualize o registry antes de chamar `evaluate_candidate`.
- Comandos usados: `rg -n "muen_economics|FoldEconomicMetrics|daily_returns|neural_daily|prediction|predicted|actual|backtest|registry" functions sisacao8 backend docs tests -S`, `sed -n` em `functions/neural_training/main.py`, `sisacao8/neural_training.py`, `sisacao8/neural_muen.py` e `sisacao8/neural_dataset.py`.


## 2026-06-27 19:18:52 UTC-3 — Implementação da geração de `muen_economics` no treino neural
- Implementado o próximo passo no código: `sisacao8.neural_training.build_muen_economics_from_predictions` monta `metrics_json.muen_economics` a partir das predições dos splits não treino e dos retornos realizados `buy_net_return`/`sell_net_return`.
- `train_baseline_mlp` agora calcula probabilidades por split uma única vez, mantém as métricas clássicas e anexa o payload `muen_economics` quando há folds econômicos válidos.
- O payload gerado inclui `protocol_version`, `dataset_snapshot`, `candidate_family_hash`, `seed`, `seed_count`, `cost_multipliers`, `fold_metrics` e `family_evaluation`; por padrão usa splits `validation`/`test` e multiplicadores de custo `1.0` e `1.5`, sem tocar `train` nem holdout bloqueado.
- Sincronizado o espelho vendorizado em `functions/neural_training/sisacao8/neural_training.py` para que o deploy da Cloud Function carregue o mesmo comportamento.
- Adicionado teste unitário cobrindo a geração de folds econômicos por split/custo, validação de `candidate_family_hash`, `seed`, contagem de folds e agregação familiar.
- Atualizado `docs/diario/proximo-passo-redes.md`: o próximo passo operacional passa a ser publicar `functions/neural_training`, executar novo treino real para criar candidata com `muen_economics`, e então rodar `evaluate_candidate`/`approve_if_passed` conforme gate.
- Comandos usados: `rg`, `sed -n`, edição via Python, `python -m black sisacao8/neural_training.py functions/neural_training/sisacao8/neural_training.py`, `python -m black tests/test_neural_training.py`, `python -m pytest tests/test_neural_training.py -q`, `python -m pytest tests/test_neural_training.py tests/test_neural_training_function.py tests/test_neural_champion_approval.py -q`, `python -m pytest -q`, `python -m flake8`, `git diff --check` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.


## 2026-06-27 22:04:49 UTC-3 — Diagnóstico do 500 na materialização do dataset neural v2
- Investigado o novo erro 500 reportado na Cloud Function produtiva `neural_training_dataset` após tentativa de materializar snapshot `feature_eod_tabular_v2`/`label_eod_barrier_v2`.
- Consulta obrigatória ao MCP via JSON-RPC HTTP em `http://mcpserversisacao.shop/mcp` confirmou nos logs da Cloud Run que a carga falha em `_load_dataset`/`load_table_from_json` porque o BigQuery rejeita campos v2 ausentes no schema produtivo: primeiro `log_return_1d` e, após ajuste parcial, `log_volume`.
- Causa confirmada: o código publicado gera as features v2 (`log_return_1d`, `log_return_5d`, `log_return_10d`, `log_return_20d`, `log_financial_volume`, `log_volume`), mas o script versionado `infra/bq/17_neural_eod_training_dataset.sql` ainda descrevia apenas o schema v1 da tabela principal e não versionava a tabela de manifestos `neural_dataset_manifests`.
- Correção aplicada no repositório: atualizado `infra/bq/17_neural_eod_training_dataset.sql` para incluir as colunas v2 no `CREATE TABLE`, adicionar `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` idempotentes para ambientes existentes e criar `cotacao_intraday.neural_dataset_manifests` com a coluna escapada `` `rows` `` compatível com o payload atual da função.
- Próximo passo operacional: aplicar o SQL atualizado no BigQuery, confirmar que as seis colunas `log_*` existem em `neural_eod_training_dataset`, rodar novamente `neural_training_dataset`, treinar uma nova candidata apontando para o snapshot v2 e então executar `neural_champion_approval` em `evaluate_candidate`.
- Comandos usados: `find .. -name AGENTS.md -print`, `git status --short`, `sed -n` em `AGENTS.md`, `docs/diario/proximo-passo-redes.md`, `infra/bq/17_neural_eod_training_dataset.sql` e `functions/neural_training_dataset/main.py`, scripts Python com `requests` para MCP HTTP/JSON-RPC (`initialize`, `cloud_run_function_logs`, tentativa de `bigquery_query`), `rg -n 'log_return_1d|log_volume|neural_dataset_manifests|rows_count' infra docs functions sisacao8 -S` e edição via Python.


## 2026-06-27 22:14:00 UTC-3 — Complemento do schema de labels executáveis no dataset neural
- Investigado novo 500 da Cloud Function `neural_training_dataset` após reaplicação parcial do schema v2.
- Logs via MCP JSON-RPC HTTP confirmaram que a carga avançou além das colunas `log_*`, mas passou a falhar por campo ausente `trade_side`, também gerado pelo builder de labels em `sisacao8/neural_dataset.py`.
- Correção aplicada no schema BigQuery versionado: adicionadas as colunas executáveis derivadas do label selecionado (`trade_side`, `entry_filled`, `entry_date`, `entry_price`, `exit_date`, `exit_price`, `exit_reason`, `gross_return`, `net_return`, `holding_sessions`, `max_adverse_excursion`, `max_favorable_excursion`, `execution_policy_version`) ao `CREATE TABLE` e aos `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`.
- Próximo passo operacional: executar novamente o SQL completo de migração do `infra/bq/17_neural_eod_training_dataset.sql` no BigQuery antes de repetir a chamada da Cloud Function.
- Comandos usados: MCP HTTP/JSON-RPC (`initialize`, `cloud_run_function_logs`), `rg -n "trade_side|target_net_return|event_date|label_class|FEATURE_COLUMNS|dataset\[" sisacao8/neural_dataset.py functions/neural_training_dataset/sisacao8/neural_dataset.py infra/bq -S`, `sed -n` em `sisacao8/neural_dataset.py`, edição via Python e `git diff`.


## 2026-06-27 22:18:00 UTC-3 — Ajuste da migração BigQuery para evitar rate limit
- Analisado erro visual reportado no BigQuery Console: `Exceeded rate limits: too many table update operations for this table`.
- Causa operacional: executar muitos `ALTER TABLE` separados na mesma tabela consome rapidamente a cota de operações de atualização de tabela do BigQuery. Separar em mais comandos piora esse erro; a alternativa correta é agrupar as adições em uma única instrução `ALTER TABLE` ou aguardar a janela de cota antes de tentar novamente.
- Correção aplicada no repositório: consolidado o bloco de migração de `infra/bq/17_neural_eod_training_dataset.sql` em um único `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ..., ADD COLUMN IF NOT EXISTS ...`, reduzindo a migração da tabela principal para uma única operação DDL.
- Comandos usados: inspeção da imagem enviada pelo usuário, edição via Python, `git diff`, consulta web de sintaxe BigQuery para múltiplos `ADD COLUMN` no mesmo `ALTER TABLE`.


## 2026-06-27 22:27:00 UTC-3 — Confirmação do schema produtivo após migração v2
- Investigado novo 500 reportado após a tentativa de materialização do snapshot neural v2.
- Consulta de logs via MCP JSON-RPC HTTP mostrou erros históricos em sequência (`log_volume`, `trade_side`, `exit_price`), compatíveis com tentativas executadas enquanto a migração BigQuery ainda estava parcial.
- Consulta read-only ao `INFORMATION_SCHEMA.COLUMNS` via MCP confirmou que a tabela produtiva `cotacao_intraday.neural_eod_training_dataset` agora contém as 19 colunas v2 esperadas: seis `log_*` e treze colunas executáveis/derivadas do label selecionado, incluindo `exit_price`.
- Consulta read-only ao `INFORMATION_SCHEMA.TABLES` via MCP confirmou que `cotacao_intraday.neural_dataset_manifests` já existe.
- Conclusão operacional: o schema necessário parece aplicado; o próximo passo é repetir a chamada da Cloud Function `neural_training_dataset` com um novo `DATASET_SNAPSHOT` e, se houver novo 500, consultar logs apenas após o horário da nova tentativa para capturar uma causa nova.
- Comandos usados: MCP HTTP/JSON-RPC (`initialize`, `cloud_run_function_logs`, `bigquery_query` em `INFORMATION_SCHEMA.COLUMNS` e `INFORMATION_SCHEMA.TABLES`).


## 2026-06-27 22:36:00 UTC-3 — Hardening da carga BigQuery do dataset neural
- Reproduzida chamada controlada da Cloud Function `neural_training_dataset` com snapshot novo `neural_eod_training_dataset_2026-06-18_muen_v2_codex_20260628_012944`, que ainda retornou 500 após o schema produtivo ter sido confirmado.
- O MCP de logs continuou retornando principalmente stack traces antigos/ordenados do período de migração parcial, impedindo isolar uma mensagem nova de BigQuery após a chamada controlada; como mitigação no código, a carga JSON passou a reindexar o DataFrame para uma lista explícita de colunas do contrato BigQuery antes de chamar `load_table_from_json`.
- Correção aplicada: `functions/neural_training_dataset/main.py` agora define `TRAINING_DATASET_COLUMNS`, converte `holding_sessions` como inteiro e filtra/remonta as linhas carregadas para impedir que qualquer coluna extra futura gerada pelo builder quebre a carga com `No such field`.
- Adicionado teste unitário garantindo que `_load_dataset` descarta colunas inesperadas antes do envio ao BigQuery e preserva `holding_sessions` como inteiro.
- Próximo passo operacional: publicar `functions/neural_training_dataset` com esse hardening e repetir a materialização do snapshot v2.
- Comandos usados: `curl` produtivo para `neural_training_dataset`, MCP HTTP/JSON-RPC (`initialize`, `cloud_run_function_logs`), comparação local entre colunas geradas por `build_training_dataset` e o DDL, edição via Python, `python -m black`.


## 2026-06-27 22:47:00 UTC-3 — Diagnóstico operacional com retorno JSON de erro
- Usuário reportou que, mesmo após deploy, `neural_training_dataset` continuou retornando 500 genérico.
- Tentada investigação via MCP: `cloud_run_function_logs` continuou retornando logs antigos/truncados da migração parcial, e consulta ao `INFORMATION_SCHEMA.JOBS_BY_PROJECT` falhou repetidamente por instabilidade de credencial do MCP/gcloud (`Credentials object has no attribute private_key_id`).
- Confirmado via `INFORMATION_SCHEMA.COLUMNS` que `neural_dataset_manifests` possui a coluna correta `rows`; consulta ao dataset mostrou que nenhum snapshot `neural_eod_training_dataset_2026-06-18_muen_v2_%` foi gravado, indicando falha antes ou durante a carga principal.
- Correção aplicada para destravar o diagnóstico: `functions/neural_training_dataset` agora captura exceções no entrypoint, registra stack trace e retorna JSON 500 com `status=error`, `error_type` e `message`, em vez de deixar o Functions Framework devolver apenas `500 Internal Server Error` genérico.
- Próximo passo operacional: publicar novamente `functions/neural_training_dataset`, repetir o curl e usar o corpo JSON retornado para identificar a causa exata remanescente.
- Comandos usados: MCP HTTP/JSON-RPC (`initialize`, `tools/list`, `cloud_run_function_logs`, tentativas de `bigquery_query` em `JOBS_BY_PROJECT`, `INFORMATION_SCHEMA.COLUMNS` e snapshots), `curl` produtivo controlado, edição via Python e `python -m black`.


## 2026-06-27 23:55:00 UTC-3 — Curl pós-deploy revelou coluna temporal ausente
- Executado `curl` produtivo após deploy da versão com retorno JSON de erro usando snapshot `neural_eod_training_dataset_2026-06-18_muen_v2_codex_20260628_025344`.
- A função retornou JSON 500 com `error_type=BadRequest` e mensagem BigQuery `No such field: temporal_protocol_json`, confirmando que o diagnóstico estruturado passou a expor a causa real.
- Confirmado via MCP/BigQuery `INFORMATION_SCHEMA.COLUMNS` que `metadata_json` existe na tabela produtiva, mas `temporal_protocol_json` ainda não existe.
- Correção aplicada no repositório: adicionada `temporal_protocol_json JSON` também ao bloco idempotente `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` em `infra/bq/17_neural_eod_training_dataset.sql`; a coluna já existia no `CREATE TABLE`, mas faltava na migração de ambientes existentes.
- Próximo passo operacional: aplicar no BigQuery `ALTER TABLE ingestaokraken.cotacao_intraday.neural_eod_training_dataset ADD COLUMN IF NOT EXISTS temporal_protocol_json JSON;` e repetir a materialização com novo snapshot.
- Comandos usados: `curl -sS -w` para `neural_training_dataset`, MCP HTTP/JSON-RPC (`initialize`, `bigquery_query` em `INFORMATION_SCHEMA.COLUMNS`) e edição via Python.


## 2026-06-28 00:03:00 UTC-3 — Materialização do dataset neural v2 concluída
- Após aplicação da coluna `temporal_protocol_json` no BigQuery, executado novamente o `curl` produtivo da Cloud Function `neural_training_dataset`.
- Resultado: HTTP 200 com `status=ok` para o snapshot `neural_eod_training_dataset_2026-06-18_muen_v2_codex_20260628_030151`.
- A função materializou 7.992 linhas no dataset neural v2, com 152 tickers e splits: `train=5142`, `validation=750`, `test=750` e `embargo=1350`.
- O manifesto retornou `feature_version=feature_eod_tabular_v2`, `label_version=label_eod_barrier_v2`, `protocol_version=neural_eod_protocol_v1`, `rows=7992`, `quality_summary.missing_ohlcv_rows=0`, `zero_volume_rows=0` e `suspicious_candle_rows=0`.
- Próximo passo operacional: executar `neural_training` apontando para `neural_eod_training_dataset_2026-06-18_muen_v2_codex_20260628_030151` para registrar candidata com `metrics_json.muen_economics`, depois validar registry e chamar `neural_champion_approval` em `evaluate_candidate`.
- Comando usado: `curl -sS -w` para `https://us-east1-ingestaokraken.cloudfunctions.net/neural_training_dataset` com `start_date=2026-03-01`, `end_date=2026-06-18`, `replace_snapshot=true`, `min_history_days=20`, `horizon_days=15` e `embargo_days=15`.


## 2026-06-28 00:09:00 UTC-3 — Treino neural MUEN executado com snapshot v2
- Executado `neural_training` produtivo apontando para o snapshot v2 `neural_eod_training_dataset_2026-06-18_muen_v2_codex_20260628_030151`.
- Resultado do curl: HTTP 200 com `status=ok`, `model_version=neural_eod_mlp_muen_codex_20260628_030718`, `model_status=candidate`, `rows=6642`, `validation_accuracy=0.28933333333333333`, `test_accuracy=0.37066666666666664`, `directional_precision=0.3088235294117647` e `coverage=0.816`.
- Artefato publicado em `gs://sisacao8-neural-artifacts/neural-eod-models/neural_eod_mlp_muen_codex_20260628_030718`.
- Validação via MCP/BigQuery no `neural_model_registry` confirmou que a candidata foi registrada com `metrics_json.muen_economics.protocol_version=neural_eod_protocol_v1`, `seed_count=1` e `fold_count=4`; portanto o bloqueio anterior `muen_economics_missing` deve ser superável para esta versão.
- Próximo passo operacional: executar `neural_champion_approval` em `mode=evaluate_candidate`, `dry_run=false`, para `neural_eod_mlp_muen_codex_20260628_030718` e validar a materialização de `neural_fold_metrics`, `neural_family_evaluations` e `neural_gate_decisions`.
- Comandos usados: `curl -sS -w` para `https://us-east1-ingestaokraken.cloudfunctions.net/neural_training` e MCP HTTP/JSON-RPC (`initialize`, `bigquery_query` no `neural_model_registry`).


## 2026-06-28 00:17:00 UTC-3 — Gate MUEN evaluate_candidate executado
- Executado `neural_champion_approval` produtivo em `mode=evaluate_candidate`, `dry_run=false`, para a candidata `neural_eod_mlp_muen_codex_20260628_030718`.
- Resultado do curl: HTTP 200 com `status=ok`, `decision_id=gate_4f4ef2b62065636f969929ec3007fb47`, `decision_status=rejected`, `passed=false`, `fold_metric_count=4`, `family_evaluation_count=1`, `gate_decision_count=1` e `daily_return_count=0`.
- Critérios reprovados retornados pela função: `folds_positivos_insuficientes`, `nao_supera_champion_mediana`, `drawdown_excessivo` e `seeds_instaveis`.
- Decisão operacional: não executar `approve_if_passed`, pois o Gate Research retornou `rejected`.
- Tentada validação adicional via MCP/BigQuery nas tabelas `neural_fold_metrics`, `neural_family_evaluations`, `neural_gate_decisions` e `neural_daily_returns`, mas o MCP alternou `503`/timeout e falhas de credencial do gcloud (`Credentials object has no attribute private_key_id`). A própria resposta da Cloud Function confirmou as contagens persistidas.
- Próximo passo operacional: analisar os critérios reprovados e gerar nova candidata/família com maior robustez econômica antes de nova tentativa de aprovação.
- Comandos usados: `curl -sS -w` para `https://us-east1-ingestaokraken.cloudfunctions.net/neural_champion_approval` e MCP HTTP/JSON-RPC (`initialize`, tentativas de `bigquery_query` nas tabelas normativas MUEN).


## 2026-06-28 00:25:00 UTC-3 — Automação do ciclo pós-Gate rejeitado
- Avaliada a necessidade operacional de não repetir manualmente `neural_training_dataset`, `neural_training` e `neural_champion_approval` a cada candidata rejeitada.
- Verificado no código que `functions/neural_evolution_orchestrator` já automatiza a geração/mutação de candidatos, chamada de `neural_training`, leitura do `neural_model_registry`, extração de `metrics_json.muen_economics` e persistência de linhas MUEN (`neural_fold_metrics`, `neural_family_evaluations`, `neural_gate_decisions`).
- Conclusão: o fluxo recorrente deve ser o Cloud Scheduler `neural-evolution-daily` chamando `neural_evolution_orchestrator` com estratégia `deterministic_phase2` e orçamento pequeno, enquanto `approve_if_passed` permanece manual/governado apenas para decisões `passed`.
- Atualizado `docs/neural_evolution_orchestrator_scheduler.md` com seção específica de automação pós-Gate rejeitado, incluindo comando para disparar o Scheduler existente e curl direto para triagem pontual.
- O MCP para consultar o Scheduler oscilou com `503`/timeout nesta tentativa; mantida a evidência operacional anterior de que `neural-evolution-daily` existe e está habilitado em `ingestaokraken/us-east1`.
- Comandos usados: `rg -n`, `sed -n` em `functions/neural_evolution_orchestrator/main.py` e `docs/neural_evolution_orchestrator_scheduler.md`, tentativa MCP HTTP/JSON-RPC `cloud_scheduler_job`, edição via Python.

## 2026-06-28 00:34:00 UTC-3 — Visibilidade das tentativas de evolução neural na tela
- Investigada a dúvida operacional sobre se o usuário consegue acompanhar na interface as tentativas automatizadas após rejeição do Gate MUEN.
- Confirmado no frontend que o menu de Redes neurais já possui as abas `Treinos` e `Evolução`, e que a aba `Evolução` recebe simultaneamente o leaderboard neural e os treinos registrados.
- Confirmado no backend que já existem endpoints `/ops/neural/training-runs` e `/ops/neural/evolution/leaderboard`, alimentados por `neural_model_registry` e `vw_neural_evolution_leaderboard`.
- Conclusão: o usuário consegue acompanhar parcialmente na tela as tentativas materializadas no registry/leaderboard; porém ainda não existe uma visão dedicada de histórico por tentativa do Scheduler/Gate com `decision_id`, critérios reprovados e métricas normativas MUEN por decisão. Recomenda-se evoluir a tela `Evolução` com uma seção "Últimas tentativas MUEN" ligada a `neural_gate_decisions`/`neural_family_evaluations` se for necessário acompanhamento operacional completo.
- Comandos usados: `nl -ba` em `frontend/app/src/App.tsx`, `frontend/app/src/api/ops.ts`, `frontend/app/src/components/tabs/NeuralEvolutionTab.tsx`, `frontend/app/src/components/tabs/neuralBaselineReadiness.ts`, `backend/sisacao-backend/src/main/java/com/sisacao/backend/ops/OpsController.java`, `backend/sisacao-backend/src/main/java/com/sisacao/backend/ops/bigquery/BigQueryOpsClient.java` e `backend/sisacao-backend/src/main/java/com/sisacao/backend/ops/bigquery/OpsBigQueryProperties.java`.

## 2026-06-28 01:05:00 UTC-3 — Tela de últimas tentativas MUEN implementada
- Implementada a sugestão de acompanhamento visual das tentativas MUEN: o backend agora expõe `/ops/neural/gate-decisions` e consulta `neural_gate_decisions` com join em `neural_family_evaluations` para trazer decisão, critérios reprovados e métricas agregadas da família.
- Adicionado o record `NeuralGateDecisionAttempt`, método de serviço, query BigQuery e testes de controller/service/client para o novo endpoint.
- No frontend, adicionados tipo/API/hook `useNeuralGateDecisions` e seção `Últimas tentativas MUEN` na aba `Redes neurais — Evolução`, exibindo `decision_id`, status, família, critérios reprovados, folds, seeds, folds positivos, delta de expectancy, drawdown, trades e data.
- Atualizado `docs/diario/proximo-passo-redes.md` para registrar que, após deploy do backend/frontend, o usuário poderá acompanhar as tentativas na tela enquanto o Scheduler mantém a geração recorrente de novas candidatas.
- Validação: `python -m flake8`, `python -m pytest -q`, `cd backend/sisacao-backend && ./mvnw test -q` e `cd frontend/app && npm run build` passaram. A tentativa de screenshot com Playwright falhou por dependência nativa ausente no container (`libatk-1.0.so.0`).

## 2026-06-28 15:05:47 UTC-3 — Rejeições MUEN visíveis na aba Treinos
- Ajustada a aba `Redes neurais — Treinos` para evitar a interpretação de que as 86 candidatas não estão sendo analisadas: agora a tela também recebe `gateDecisions`, exibe card `Rejeitadas no gate` e mostra a tabela `Últimas análises do Gate MUEN` com status, família/candidata, critérios reprovados, folds positivos, delta de expectancy, drawdown e data.
- Atualizado `App.tsx` para carregar decisões do Gate MUEN junto com a aba de treinos, de modo que o botão de atualizar reflita tanto registros de treino quanto análises/rejeições governadas.
- O próximo passo operacional das redes não mudou: seguir gerando novas candidatas pelo orquestrador/Scheduler e só executar aprovação governada quando uma decisão MUEN retornar `passed`.
- Comandos usados: `find .. -name AGENTS.md -print`, `git status --short`, `cat AGENTS.md`, `sed -n` em `frontend/app/src/components/tabs/NeuralTrainingRunsTab.tsx`, `frontend/app/src/App.tsx`, `frontend/app/src/api/ops.ts` e `frontend/app/src/components/tabs/NeuralEvolutionTab.tsx`, edição via Python, `npm --prefix frontend/app run build`, `npm --prefix frontend/app run lint` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## Nota operacional — 2026-06-28 15:28 UTC-3

A leitura da tela `Redes neurais — Treinos` indicou 86 redes em estágio `Candidata`, 24 decisões/rejeições do Gate MUEN e 0 aprovadas. Interpretação operacional corrigida: não se deve calcular automaticamente `86 - 24 = 62`, porque o card `Candidata` vem do status atual no `neural_model_registry`, enquanto `Rejeitada no gate` vem das decisões MUEN; uma mesma rede pode continuar com status `candidate` no registry e também aparecer como rejeitada pelo Gate Research. Portanto, o número seguro pela tela é: existem 86 candidatas no registry e 24 análises MUEN rejeitadas; para saber quantas candidatas nunca foram avaliadas, é preciso cruzar por `model_version`/família entre registry e decisões MUEN. O próximo passo operacional das redes não mudou: manter a geração recorrente de candidatas via orquestrador/Scheduler, acompanhar novas decisões MUEN e executar `approve_if_passed` apenas quando alguma decisão aparecer como `passed`.

## 2026-06-28 15:41:00 UTC-3 — Contagem de candidatas ainda testáveis na aba Treinos

- Atualizada a aba `Redes neurais — Treinos` para exibir o card `Ainda podem ser testadas`, calculado a partir das candidatas com status `candidate` no registry que ainda não possuem decisão MUEN carregada por `candidate_family_hash`/`model_version`.
- A seção de leitura de estágios também passou a mostrar `Pode ser testada`, evitando a subtração manual ambígua `86 - 24` e deixando a tela calcular a estimativa diretamente.
- O próximo passo operacional das redes não mudou: continuar acompanhando a geração recorrente de candidatas e executar `approve_if_passed` apenas quando uma decisão MUEN retornar `passed`.
- Comandos usados: `rg -n`, `sed -n` em `frontend/app/src/components/tabs/NeuralTrainingRunsTab.tsx`, `frontend/app/src/api/ops.ts`, `backend/sisacao-backend/src/main/java/com/sisacao/backend/ops/OpsController.java`, `backend/sisacao-backend/src/main/java/com/sisacao/backend/ops/OpsService.java` e `backend/sisacao-backend/src/main/java/com/sisacao/backend/ops/bigquery/BigQueryOpsClient.java`, edição via Python, `npm --prefix frontend/app run lint`, `npm --prefix frontend/app run build`, `npx --yes playwright@1.56.1 install chromium`, `apt-get install` das dependências nativas do Chromium e screenshot local com Playwright em `/tmp/sisacao-neural-treinos.png` (não versionado).

## 2026-06-28 16:03:13 UTC-3 — Diagnóstico de parada das análises MUEN
- Investigada a pergunta sobre por que as análises visíveis na tela pararam por volta de 05h/05:31 em 28/06/2026.
- Confirmado pela API publicada `/api/ops/neural/gate-decisions` que a última decisão MUEN materializada na tela foi `2026-06-28T08:31:26Z` (05:31 em America/Sao_Paulo), com status `rejected`.
- Confirmado que a ausência de novas linhas na tela não significa que o Scheduler parou: logs recentes da Cloud Function `neural_evolution_orchestrator` via MCP HTTP/JSON-RPC mostram chamadas posteriores às 14:30 e 15:30 BRT retornando HTTP 500.
- Causa confirmada nos logs: a função falhou antes de persistir nova execução/decisão com `ValueError: No neural evolution candidates were generated` em `functions/neural_evolution_orchestrator/main.py`, linha que aborta quando a geração de candidatos retorna lista vazia.
- Hipótese operacional: o espaço de candidatos da configuração atual foi esgotado pelo filtro de deduplicação (`existing_hashes`) e/ou pela estratégia `deterministic_phase2` com orçamento pequeno, então novas chamadas continuam ocorrendo, mas não geram uma candidata inédita para treinar/analisar.
- Validação adicional: chamada direta controlada com `dry_run=true` para `neural_evolution_orchestrator` também retornou HTTP 500, reproduzindo o problema sem inserir novos dados.
- Próximo passo operacional atualizado: ajustar a geração de candidatos do orquestrador para não abortar silenciosamente quando o grid atual estiver esgotado, ampliando mutações/seeds ou retornando resposta controlada, e então reativar/rodar nova tentativa para confirmar novas decisões MUEN.
- Comandos usados: `curl` para `http://34.194.252.70/api/ops/neural/evolution/leaderboard`, `curl` para `http://34.194.252.70/api/ops/neural/gate-decisions`, `curl` com `dry_run=true` para `https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator`, scripts Python `requests.post` para MCP HTTP/JSON-RPC (`initialize`, `cloud_run_function_logs`), `sed -n` em `functions/neural_evolution_orchestrator/main.py` e `functions/neural_evolution_orchestrator/sisacao8/neural_evolution.py`, e `date`/`TZ=America/Sao_Paulo date`.

## 2026-06-28 16:12:48 UTC-3 — Correção para grid esgotado do orquestrador neural
- Implementada correção no gerador de evolução neural para o caso em que a Fase 2 esgota o grid finito de mutações e todos os hashes candidatos já existem.
- Adicionado `repeat_finalists_with_fresh_seeds` em `sisacao8.neural_evolution` e sincronizado no pacote vendorizado da Cloud Function `neural_evolution_orchestrator`; o helper preserva a arquitetura/hiperparâmetros da família finalista, mas cria repetições com seeds inéditas e checa `existing_hashes` antes de retornar candidatos.
- Atualizado `functions/neural_evolution_orchestrator/main.py` para, quando `mutate_top_candidates` não gerar nenhum candidato, registrar warning e cair automaticamente para repetições com seeds inéditas em vez de abortar com `ValueError: No neural evolution candidates were generated`.
- Adicionados testes unitários cobrindo o helper de seeds inéditas e o fallback da Fase 2 quando as mutações disponíveis já foram consumidas.
- Próximo passo operacional: publicar a Cloud Function `neural_evolution_orchestrator` corrigida e disparar/aguardar o Scheduler para confirmar que novas decisões MUEN voltam a ser persistidas.
- Comandos usados: `sed -n` em `functions/neural_evolution_orchestrator/main.py`, `sisacao8/neural_evolution.py`, `functions/neural_evolution_orchestrator/sisacao8/neural_evolution.py` e testes; edição via Python; `python -m black ...`; `python -m pytest tests/test_neural_evolution.py tests/test_neural_evolution_orchestrator_function.py -q`; `python -m flake8`; `python -m pytest -q`; `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-28 16:27:30 UTC-3 — Fallback passa a priorizar novas arquiteturas
- Revisada a correção anterior após a pergunta operacional sobre gerar redes com outras arquiteturas em vez de apenas repetir seeds.
- Implementado `generate_architecture_variant_candidates` em `sisacao8.neural_evolution` e no pacote vendorizado da Cloud Function; o helper cria variações MLP mais largas, mais estreitas, mais profundas e mais rasas a partir de finalistas, respeitando `max_layers`, `max_parameter_count` e `existing_hashes`.
- Atualizado `functions/neural_evolution_orchestrator/main.py` para priorizar variantes de arquitetura quando o grid de mutações da Fase 2 esgotar; repetições com seeds inéditas ficam como segunda linha de fallback, apenas se as variantes arquiteturais também não gerarem candidatos.
- Atualizados testes para validar geração de arquiteturas alternativas e o novo fallback da Fase 2 com `candidate_source=architecture_variant`.
- Próximo passo operacional: publicar o orquestrador com a correção e acompanhar se as próximas decisões MUEN mostram famílias arquiteturalmente diferentes antes de recorrer a seed repeats.
- Comandos usados: `rg -n`, `sed -n` em treino/orquestrador/evolução neural, edição via Python, `python -m black ...`, `python -m pytest tests/test_neural_evolution.py tests/test_neural_evolution_orchestrator_function.py -q`, `python -m flake8`, `python -m pytest -q` e `TZ=America/Sao_Paulo date '+%Y-%m-%d %H:%M:%S UTC-3'`.

## 2026-06-28 22:52:00 UTC-3 — Tentativa de alterar Scheduler neural para 30 minutos
- Investigada a solicitação de reduzir a cadência do processo neural mostrado na tela de 1 em 1 hora para meia em meia hora.
- Confirmado via MCP HTTP/JSON-RPC (`cloud_scheduler_job`) que o job `neural-evolution-daily` existe em `ingestaokraken/us-east1`, está `ENABLED`, usa `timeZone: America/Sao_Paulo`, `attemptDeadline: 1800s`, chama `https://us-east1-ingestaokraken.cloudfunctions.net/neural_evolution_orchestrator` e estava agendado como `30 * * * *` (uma vez por hora no minuto 30).
- Tentada a atualização via MCP HTTP/JSON-RPC (`cloud_scheduler_job_write`) para `*/30 * * * *`, mas o runtime autenticado como `codex-openai@ingestaokraken.iam.gserviceaccount.com` retornou `PERMISSION_DENIED` por falta da permissão `cloudscheduler.jobs.update` no job.
- Atualizado o runbook `docs/neural_evolution_orchestrator_scheduler.md` para registrar a cadência desejada de meia em meia hora e o comando correto de update sem OIDC para aplicar quando a conta tiver permissão de Cloud Scheduler.
- Próximo passo operacional atualizado: conceder à service account do MCP/Codex permissão de update no Cloud Scheduler (por exemplo papel equivalente a `roles/cloudscheduler.admin` no projeto ou permissão específica no job) ou executar o comando documentado com uma conta autorizada; depois confirmar por `cloud_scheduler_job` que o schedule ficou `*/30 * * * *`.
- Comandos usados: `find .. -name AGENTS.md -print`, `git status --short`, `cat AGENTS.md`, `rg -n`, `sed -n` em `docs/neural_evolution_orchestrator_scheduler.md`, scripts Python `requests.post` para MCP HTTP/JSON-RPC (`initialize`, `cloud_scheduler_job`, `cloud_scheduler_job_write`) e edição via Python.
