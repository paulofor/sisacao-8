# Próximo passo operacional das redes neurais — parte 2

## 2026-07-11 — Materializar predições e sinais do champion NEV

O champion neural NEV `Apolo NEV` está aprovado no registry, mas a tela dedicada mostrou `predictions=[]` e `signals=[]` no endpoint produtivo `GET http://34.194.252.70/api/ops/neural/champion-monitoring`. Isso não indica que o champion foi perdido; indica que o pipeline pós-aprovação ainda não materializou linhas nas tabelas operacionais consumidas pela tela.

Causa operacional atualizada: os schedulers foram criados posteriormente, mas o endpoint `neural_eod_predictions` ainda retornou HTTP 404 no teste manual de 2026-07-11. Sem a função de predições publicada e sem linhas em `neural_eod_predictions`, `eod_signals` com `signal_source=neural` retorna vazio e não cria sinais em `sinais_eod`.

Próximo passo imediato:

1. Publicar primeiro a Cloud Function `neural_eod_predictions`; o teste manual de 2026-07-11 retornou HTTP 404 para esse endpoint, então a cadeia neural ainda não consegue materializar predições.
2. Depois do deploy, com uma conta autorizada, executar manualmente a cadeia EOD neural para a última data de pregão válida:
   - chamar `https://us-east1-ingestaokraken.cloudfunctions.net/neural_eod_predictions` com `force=true` e `date_ref=<último pregão>`;
   - em seguida chamar `https://us-east1-ingestaokraken.cloudfunctions.net/eod_signals` com `force=true`, `signal_source=neural` e a mesma `date_ref` se necessário.
3. Validar na API `/api/ops/neural/champion-monitoring` que as tabelas da tela passaram a retornar predições e sinais.
4. Ajustar, ou pedir a um operador com permissão para ajustar, os schedulers recorrentes para depois da ingestão diária oficial (`get_stock_data` às 20:00 BRT), porque a rede lê `cotacao_ohlcv_diario`:
   - `neural-eod-predictions-daily`: preferencialmente `10 23 * * 1-5`, `America/Sao_Paulo`, POST para `neural_eod_predictions`;
   - `neural-eod-signals-daily`: preferencialmente `20 23 * * 1-5` ou depois, `America/Sao_Paulo`, POST para `eod_signals` com `{"signal_source":"neural","force":false}`.
5. Enquanto as funções estiverem públicas, criar/atualizar os jobs sem OIDC; só incluir OIDC após validar service account, papel invoker e permissão `iam.serviceAccountUser` conforme o runbook do projeto.
6. Se for necessário rodar antes das 20:00, adicionar antes uma validação de frescor: `cotacao_ohlcv_diario` precisa ter linhas para o `date_ref` do último pregão; caso contrário, não processar sinais neurais.
7. Depois da materialização, monitorar pelo menos 5 pregões na aba `Champion NEV` antes de discutir qualquer uso com capital real.

Observação de diagnóstico: o MCP HTTP/JSON-RPC em `http://mcpserversisacao.shop/mcp` apresentou `503`/timeouts durante a tentativa de consulta BigQuery/logs, então a confirmação desta etapa usou a API backend produtiva. Manter a regra de não usar HTTPS para o MCP.
