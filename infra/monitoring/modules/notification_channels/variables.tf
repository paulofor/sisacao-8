variable "project_id" {
  type        = string
  description = "Projeto onde os canais serão criados."
}

variable "email" {
  type        = string
  description = "Endereço de e-mail para notificações."
  default     = ""
}

variable "webhook_url" {
  type        = string
  description = "Webhook HTTP/Slack/Teams para notificações."
  default     = ""
}
