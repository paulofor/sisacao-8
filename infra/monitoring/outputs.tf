output "notification_channels" {
  value = module.notification_channels.channel_ids
}

output "alert_policies" {
  value = {
    job_error   = module.alert_policies.job_error_policy
    dq_failure  = module.alert_policies.dq_failure_policy
    cotahist    = module.alert_policies.cotahist_policy
    silence     = module.alert_policies.silence_policies
  }
}
