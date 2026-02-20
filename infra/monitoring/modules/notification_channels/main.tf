resource "google_monitoring_notification_channel" "email" {
  count        = length(var.email) > 0 ? 1 : 0
  project      = var.project_id
  display_name = "Sisacao Ops Email"
  type         = "email"
  labels = {
    email_address = var.email
  }
}

resource "google_monitoring_notification_channel" "webhook" {
  count        = length(var.webhook_url) > 0 ? 1 : 0
  project      = var.project_id
  display_name = "Sisacao Ops Webhook"
  type         = "webhook"
  labels = {
    url = var.webhook_url
  }
}
