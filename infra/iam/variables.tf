variable "project_id" {
  description = "ID do projeto GCP que hospeda as funções."
  type        = string
}

variable "dataset_id" {
  description = "Dataset BigQuery onde os jobs precisam de acesso."
  type        = string
  default     = "cotacao_intraday"
}

variable "job_names" {
  description = "Lista de funções Cloud Functions/Run que terão service accounts dedicadas."
  type        = list(string)
  default = [
    "get_stock_data",
    "intraday_candles",
    "eod_signals",
    "backtest_daily",
    "dq_checks",
    "alerts",
    "google_finance_price",
  ]
}

variable "scheduler_account_id" {
  description = "Prefixo do account_id utilizado pela service account do Cloud Scheduler."
  type        = string
  default     = "sa-scheduler-invoker"
}
