# Fase 2 MUEN v1 — Dataset point-in-time

**Status:** executada  
**Data:** 2026-06-24  
**Protocolo:** `neural_eod_protocol_v1`  
**Feature version:** `feature_eod_tabular_v2`  
**Label version:** `label_eod_barrier_v2`  
**Universe version:** `b3_point_in_time_v1`

## Objetivo

Implementar os controles mínimos da Fase 2 do MUEN v1 para que cada snapshot do dataset neural EOD seja auditável, reproduzível e protegido contra vazamento temporal antes de avançar para walk-forward, baselines e gates.

## Entregas implementadas

1. **Manifesto imutável do snapshot**
   - Criado `DatasetSnapshotManifest` em `sisacao8.neural_dataset`.
   - Criado helper `build_dataset_manifest` com:
     - snapshot, protocolo, feature, label e universe version;
     - hash estável da query de extração;
     - hash estável do contrato de código;
     - período coberto;
     - quantidade de linhas e tickers;
     - distribuição de splits e labels;
     - resumo de qualidade;
     - premissas de custo;
     - políticas de calendário, corporate actions e sobrevivência.

2. **Materialização do manifesto no BigQuery**
   - A Cloud Function `neural_training_dataset` passa a gravar uma linha por snapshot em `cotacao_intraday.neural_dataset_manifests`.
   - Cada linha do dataset materializado recebe `metadata_json` com `protocol_version`, hashes do manifesto e política de sobrevivência.

3. **Controle de embargo coerente com horizonte**
   - A função agora rejeita payloads em que `embargo_days < horizon_days`, evitando splits com labels atravessando fronteiras sem embargo suficiente.

4. **Features tabulares v2**
   - Atualizado `FEATURE_VERSION` para `feature_eod_tabular_v2`.
   - Adicionadas features iniciais mais aderentes ao MUEN:
     - `log_return_1d`, `log_return_5d`, `log_return_10d`, `log_return_20d`;
     - `log_financial_volume`;
     - `log_volume`.
   - As colunas OHLCV nominais permanecem no dataset por compatibilidade com o treinador atual, mas passam a ser explicitamente classificadas como legado a reavaliar antes dos gates econômicos.

5. **Sincronização de pacote embarcado**
   - Sincronizada a cópia de `sisacao8.neural_dataset` dentro de `functions/neural_training_dataset/`.
   - Sincronizada a cópia de `sisacao8.neural_dataset` dentro de `functions/neural_training/` para reduzir risco de divergência em deploy.

## Controles contra leakage cobertos nesta fase

- Features são calculadas por ticker usando candles até `reference_date`.
- Labels usam apenas candles futuros para supervisão histórica, com `valid_for > reference_date`.
- Split temporal mantém embargo configurado entre treino/validação/teste.
- A Cloud Function impede embargo menor que o horizonte do label.
- O manifesto registra hashes e versões para detectar mudanças de query/código/protocolo.

## Limitações assumidas

- O universo `b3_point_in_time_v1` ainda depende da disponibilidade operacional da tabela/fonte point-in-time; a política fica registrada no manifesto como `acao_bovespa_point_in_time_when_available`.
- Corporate actions seguem a política da tabela diária de origem; a validação formal da política de ajuste fica para a evolução do contrato de dados.
- OHLCV nominal bruto ainda é carregado para compatibilidade com `FEATURE_COLUMNS` do MLP atual; a remoção/transformação completa deve ser tratada junto com Fase 3+ para não quebrar inferência e artefatos existentes.

## Critério de aceite desta fase

A Fase 2 fica aceita quando os testes locais confirmarem:

- criação do dataset com `feature_eod_tabular_v2` e `label_eod_barrier_v2`;
- criação de manifesto com hashes, versões, distribuição de labels/splits e qualidade;
- gravação do manifesto pela Cloud Function;
- rejeição de embargo menor que o horizonte.
