output "service_accounts" {
  description = "Service accounts criadas para cada job."
  value       = { for name, sa in google_service_account.jobs : name => sa.email }
}

output "scheduler_service_account" {
  description = "Service account utilizada pelo Cloud Scheduler para invocar os jobs."
  value       = google_service_account.scheduler.email
}
