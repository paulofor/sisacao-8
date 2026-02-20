variable "project_id" {
  type        = string
  description = "Projeto alvo."
}

variable "notification_channels" {
  type        = list(string)
  description = "IDs dos canais de notificação."
  default     = []
}

variable "silence_windows" {
  description = "Mapa de jobs e suas janelas máximas de silêncio (em segundos)."
  type        = map(number)
  default = {
    get_stock_data    = 21600
    eod_signals       = 18000
    intraday_candles  = 7200
  }
}
