output "job_error_policy" {
  value = google_monitoring_alert_policy.job_error.name
}

output "dq_failure_policy" {
  value = google_monitoring_alert_policy.dq_failure.name
}

output "cotahist_policy" {
  value = google_monitoring_alert_policy.cotahist_failure.name
}

output "silence_policies" {
  value = { for name, policy in google_monitoring_alert_policy.silence : name => policy.name }
}
