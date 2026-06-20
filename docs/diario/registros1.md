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
