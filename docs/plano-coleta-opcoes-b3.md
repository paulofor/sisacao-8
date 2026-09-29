# Plano inicial para coleta de opções da B3

## Resposta curta

Sim, é possível coletar as principais opções negociadas na B3. A implantação
deve ser feita como um pipeline separado do pipeline de ações: uma opção tem
vencimento, preço de exercício, tipo (compra ou venda), ativo-objeto e pode
deixar de existir pouco tempo depois. Por isso, não é seguro tratar opções como
uma lista fixa de tickers nem misturá-las diretamente às tabelas de ações.

Este documento registra somente a decisão e o desenho inicial. Nenhuma nova
função ou tabela foi criada nesta etapa.

## Escopo recomendado para o piloto

1. Começar por opções de compra e venda sobre um conjunto pequeno de
   ativos-objeto líquidos, definido por configuração, sem fixar séries de
   opções no código.
2. Atualizar diariamente o cadastro de contratos e selecionar as séries por
   critérios objetivos:
   - vencimento entre 7 e 90 dias;
   - negócios e volume financeiro mínimos;
   - preferência por contratos com preço de exercício próximo ao preço do
     ativo-objeto;
   - exclusão de cotações sem negócios, spreads inválidos ou contratos já
     vencidos.
3. Coletar no piloto candles diários, quantidade, número de negócios e volume
   financeiro. Intraday deve ser uma segunda fase, após confirmar fonte,
   limites, licença e qualidade dos dados.
4. Tornar os limites configuráveis no BigQuery para que a definição de
   “principais” seja auditável e possa evoluir sem novo deploy.

## Fontes e restrições

- O COTAHIST oficial já usado pelo projeto é candidato para preços e volumes
  diários. Entretanto, o parser atual extrai somente ticker e OHLCV; ele não
  preserva os campos necessários para identificar e filtrar corretamente uma
  opção, como mercado, especificação do papel, preço de exercício e vencimento.
- O cadastro de instrumentos da B3, ou um provedor contratado que entregue os
  mesmos atributos, deve ser a fonte da dimensão de contratos.
- Antes de ativar coleta intraday, é obrigatório validar termos de uso,
  redistribuição, latência, limites e estabilidade da fonte escolhida. Scraping
  de página pública não deve ser considerado uma fonte produtiva de cadeia de
  opções.

## Modelo de dados proposto

Criar um dataset lógico separado, por exemplo `opcoes_b3`, com pelo menos:

- `instrumentos`: `option_symbol`, `underlying_symbol`, `option_type`,
  `strike`, `expiration_date`, `exercise_style`, `contract_multiplier`,
  `status`, `source`, `source_updated_at`, `ingested_at`;
- `candles_diarios`: chave idempotente (`option_symbol`, `trade_date`) e campos
  OHLC, quantidade, número de negócios, volume financeiro, fonte, instante de
  ingestão e flags de qualidade;
- `universo_diario`: contratos selecionados em cada data, critérios aplicados,
  versão da configuração e motivo de inclusão/exclusão;
- numa fase posterior, `quotes_intraday`, incluindo bid, ask, último negócio,
  timestamp da fonte e timestamp de ingestão.

Não calcular volatilidade implícita ou gregas até que preço do ativo-objeto,
taxa, dividendos, convenção de calendário e timestamp estejam definidos e
alinhados point-in-time.

## Qualidade e segurança operacional

- Validar unicidade, vencimento, strike positivo, tipo válido e vínculo com o
  ativo-objeto.
- Distinguir ausência de negociação de preço zero e nunca preencher períodos
  ilíquidos silenciosamente.
- Monitorar cobertura por vencimento, atraso da fonte, contratos sem cadastro,
  duplicidades e mudanças anormais de universo.
- Particionar cotações por data e clusterizar por ativo-objeto e símbolo da
  opção para controlar custo de consulta.
- Manter opções fora dos sinais e redes neurais atuais até existir histórico
  suficiente, testes point-in-time e uma decisão explícita de integração.

## Etapas de implementação após aprovação

1. Confirmar a fonte oficial/contratada e documentar o dicionário de campos e
   as permissões de uso.
2. Definir os ativos-objeto iniciais e os thresholds numéricos de liquidez.
3. Ampliar o parser em um módulo próprio para preservar os atributos de opções
   e criar testes com fixtures oficiais.
4. Provisionar as tabelas e implementar carga diária idempotente, inicialmente
   em modo de observação.
5. Executar pelo menos 20 pregões de piloto e auditar completude, duplicidade,
   atraso, liquidez e continuidade antes de considerar intraday ou analytics.

## Critério de aceite do piloto

O piloto será considerado estável quando, por 20 pregões consecutivos, registrar
o universo selecionado e seus candles sem duplicidades, com atributos de
contrato completos, rastreabilidade da fonte e alertas explícitos para lacunas.
Esse aceite não autoriza negociação nem integração automática com as redes
neurais.
