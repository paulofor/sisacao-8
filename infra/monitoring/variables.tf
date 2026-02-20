variable "project_id" {
  description = "Projeto alvo para canais e alertas."
  type        = string
}

variable "email" {
  description = "E-mail principal para notificações."
  type        = string
  default     = ""
}

variable "webhook_url" {
  description = "Webhook HTTPS (Slack/Teams/PagerDuty) para notificações."
  type        = string
  default     = ""
}

variable "silence_windows" {
  description = "Mapa de jobs para a janela máxima de silêncio em segundos."
  type        = map(number)
  default = {
    get_stock_data    = 21600
    eod_signals       = 18000
    intraday_candles  = 7200
  }
}
