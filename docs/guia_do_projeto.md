# Guia do projeto

Este documento resume o que já existe no repositório e indica a estratégia recomendada para operar as cargas de cotações.

## Visão geral

O projeto **sisacao-8** automatiza a coleta de cotações da B3 e o carregamento dos dados em tabelas do BigQuery. O fluxo combina
funções serverless para ingestão (Cloud Functions e Cloud Run), consultas agendadas para derivar sinais e integrações opcionais
para envio de alertas. A infraestrutura já disponível permite construir uma rotina diária de atualização e monitoramento das
séries de preços sem necessidade de serviços adicionais.

## Estrutura atual do repositório

- `config/`: contém o arquivo `env.example` com as variáveis mínimas necessárias para definir projeto, dataset e região no GCP.
- `functions/get_stock_data/`: Cloud Function que baixa o arquivo oficial da B3 (`COTAHIST_D{data}.ZIP`), extrai as cotações
  solicitadas e insere os dados na tabela dedicada `ingestaokraken.cotacao_intraday.cotacao_fechamento_diario` usando o cliente do BigQuery.
- `functions/google_finance_price/`: função HTTP pensada para Cloud Run que consulta a lista de tickers ativos no BigQuery,
  busca o último preço no Google Finance via *scraping* e grava os resultados na tabela `ingestaokraken.cotacao_intraday.cotacao_bovespa`.
- `functions/alerts/`: função HTTP que consulta a tabela de sinais (`ingestaokraken.cotacao_intraday.signals_oscilacoes`) e, se configurada com `BOT_TOKEN` e
  `CHAT_ID`, envia um resumo para um bot do Telegram.
- `infra/bq/`: scripts SQL de apoio, incluindo `cotacao_fechamento_diario.sql` e `signals_oscilacoes.sql`, usados nas consultas
  agendadas do BigQuery.
- `docs/dataset_detected.md`: documentação sobre o dataset `cotacao_intraday`, destacando as tabelas `cotacao_bovespa`
  (intraday) e `cotacao_fechamento_diario` (oficial de fechamento) mapeadas no projeto `ingestaokraken`.
- `docs/monitoramento.md`: instruções para configurar a *scheduled query* diária e montar o painel no Looker Studio.
- `scripts/local_test.py`: guia rápido para executar as funções localmente com o `functions-framework`.
- `tests/`: suíte inicial de testes automatizados.

## Fluxo de dados recomendado

1. **Carga oficial diária:** a função `get_stock_data` deve ser agendada (ou acionada manualmente) após o fechamento do pregão.
   Ela baixa o arquivo de cotações diário da B3, filtra os tickers desejados e grava as informações de preço e data na tabela
   `ingestaokraken.cotacao_intraday.cotacao_fechamento_diario`.
2. **Atualização intradiária opcional:** a função `google_finance_price` pode ser implantada como serviço HTTP para complementar
   as cotações oficiais com preços próximos ao tempo real. Ela consulta a lista de ativos marcada como `ativo = TRUE` na tabela
   `ingestaokraken.cotacao_intraday.acao_bovespa`, busca os preços no Google Finance e insere os registros no BigQuery.
3. **Derivação de sinais:** utilize a consulta `infra/bq/signals_oscilacoes.sql` como *scheduled query* diária (conforme descrito
   em `docs/monitoramento.md`) para gerar a tabela `ingestaokraken.cotacao_intraday.signals_oscilacoes` com os indicadores calculados sobre a base intraday.
4. **Alertas e monitoramento:** a função `alerts` resume os sinais do dia corrente e pode publicar mensagens no Telegram. O painel
   sugerido no Looker Studio consome a mesma tabela de sinais para acompanhamento visual.

## Estratégia operacional

1. **Preparação de ambiente:** copie `config/env.example` para `.env`, defina `GCP_PROJECT`, `BQ_TABLE` e outras variáveis e
   instale as dependências via `requirements.txt`.
2. **Agendamento da ingestão:** configure uma Cloud Scheduler ou outra automação para invocar `get_stock_data` diariamente.
   Caso precise de dados intradiários, disponibilize `google_finance_price` em Cloud Run e acione-a em janelas mais curtas.
3. **Processamento analítico:** mantenha a *scheduled query* `signals_oscilacoes` ativa para produzir os indicadores necessários.
4. **Alertas e painel:** habilite a função `alerts` com os segredos do Telegram para receber notificações e siga `docs/monitoramento.md`
   para publicar o dashboard no Looker Studio.
5. **Evolução contínua:** registre novas funções ou ajustes de pipeline neste diretório `docs/` para manter a visão do projeto
   atualizada e facilitar a colaboração entre times de dados e engenharia.

