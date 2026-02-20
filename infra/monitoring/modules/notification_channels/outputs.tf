output "channel_ids" {
  value = concat(
    google_monitoring_notification_channel.email[*].name,
    google_monitoring_notification_channel.webhook[*].name,
  )
}
