# Próximo passo operacional das redes neurais — parte 2

## 2026-07-10 — Primeira família NEV aprovada no Gate MUEN, ainda sem promoção automática

Foi executado o diagnóstico recomendado em `neural_fold_metrics` e `neural_daily_returns` para entender as rejeições das famílias NEV tabulares. A causa operacional encontrada foi concentração de perdas em poucos tickers de cauda: na família `p48/m05/t50 + NEV`, os principais detratores foram `ONCO3` (`delta_return=-0.42`, 6 trades), `VVEO3` (`-0.14`, 2 trades) e `AMBP3` (`-0.14`, 2 trades), enquanto `PCAR3`, `RCSL3` e `RAIZ4` contribuíram positivamente.

Com a hipótese confirmada, foi executada uma shadow `p48/m05/t50 + NEV` bloqueando `ONCO3`, `VVEO3` e `AMBP3`. A rodada de 1 seed melhorou a mediana (`median_delta=0.01261978384427366`) e gerou `positive_folds=2`, mas ainda falhou por `folds_positivos_insuficientes` e `seeds_instaveis`.

Depois foi executada uma rodada shadow pequena com 3 candidatas/seeds/variações controladas para a política `neural_eod_phase3_tabular_bottleneck_mlp_p48_m05_t50_block3_nev_rcsl3_grid3`. Essa família passou no Gate MUEN: `passed=true`, `decision_status=passed`, `seeds=3`, `stable_across_seeds=true`, `positive_folds=8`, `total_trades=30`, `median_delta=0.018891465677179982`, `max_drawdown=0.195643` e `failed_criteria=[]`.

Estado de prontidão: pela primeira vez há uma família neural que passou no teste de qualidade/Gate MUEN. Porém os modelos continuam no `neural_model_registry` como `status=candidate`, e não houve promoção automática, Scheduler nem ativação produtiva. Portanto, a família está apta para revisão operacional e validação shadow controlada, mas não deve ser usada em produção sem aprovação manual explícita.

Próximo passo operacional: não promover automaticamente. Validar a família aprovada em nível de modelo/candidata: revisar os três `model_version` candidatos, confirmar métricas individuais, inspecionar `neural_daily_returns` por ticker/data/fold depois do bloqueio, e decidir manualmente se vale abrir uma etapa de paper-trading/shadow monitorado. Se aprovada manualmente, registrar a decisão e só então avaliar promoção controlada; se não, continuar busca calibrada em torno de `p48/m05/t50 + block3 + NEV`, sem recorrentes/TCN ainda.
