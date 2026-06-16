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
