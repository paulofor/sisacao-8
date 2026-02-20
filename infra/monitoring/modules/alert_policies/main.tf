locals {
  silence = var.silence_windows
}

resource "google_logging_metric" "job_ok" {
  project = var.project_id
  name    = "sisacao_job_ok"
  filter  = "jsonPayload.status=\"OK\" AND jsonPayload.job_name!\=\"\""

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
    labels {
      key         = "job_name"
      value_type  = "STRING"
      description = "Job responsável pela execução"
    }
  }

  label_extractors = {
    job_name = "EXTRACT(jsonPayload.job_name)"
  }
}

resource "google_logging_metric" "job_error" {
  project = var.project_id
  name    = "sisacao_job_error"
  filter  = "jsonPayload.status=\"ERROR\" AND jsonPayload.job_name!\=\"\""

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }

  label_extractors = {
    job_name = "EXTRACT(jsonPayload.job_name)"
  }
}

resource "google_logging_metric" "dq_fail" {
  project = var.project_id
  name    = "sisacao_dq_fail"
  filter  = "jsonPayload.job_name=\"dq_checks\" AND jsonPayload.status=\"WARN\""

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }
}

resource "google_logging_metric" "cotahist_failure" {
  project = var.project_id
  name    = "sisacao_cotahist_failure"
  filter  = "jsonPayload.reason=\"cotahist_download_failed\""

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }
}

locals {
  documentation = <<-EOT
Consultar o RUNBOOK.md para o passo a passo de mitigação. Sempre registrar o run_id e o motivo do disparo.
EOT
}

resource "google_monitoring_alert_policy" "job_error" {
  project               = var.project_id
  display_name          = "Sisacao - Falha em jobs"
  combiner              = "OR"
  notification_channels = var.notification_channels

  documentation {
    content  = local.documentation
    mime_type = "text/markdown"
  }

  alert_strategy {
    notification_rate_limit {
      period = "900s"
    }
  }

  conditions {
    display_name = "job_error_count"
    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/sisacao_job_error\""
      duration        = "0s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      trigger {
        count = 1
      }
      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_MEAN"
      }
    }
  }
}

resource "google_monitoring_alert_policy" "dq_failure" {
  project               = var.project_id
  display_name          = "Sisacao - DQ FAIL"
  notification_channels = var.notification_channels
  combiner              = "OR"

  documentation {
    content  = local.documentation
    mime_type = "text/markdown"
  }

  alert_strategy {
    notification_rate_limit {
      period = "900s"
    }
  }

  conditions {
    display_name = "dq_fail_event"
    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/sisacao_dq_fail\""
      duration        = "0s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      trigger {
        count = 1
      }
      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_MEAN"
      }
    }
  }
}

resource "google_monitoring_alert_policy" "cotahist_failure" {
  project               = var.project_id
  display_name          = "Sisacao - Falha download COTAHIST"
  notification_channels = var.notification_channels
  combiner              = "OR"

  documentation {
    content  = local.documentation
    mime_type = "text/markdown"
  }

  alert_strategy {
    notification_rate_limit {
      period = "900s"
    }
  }

  conditions {
    display_name = "cotahist_failure_event"
    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/sisacao_cotahist_failure\""
      duration        = "0s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      trigger {
        count = 1
      }
      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_MEAN"
      }
    }
  }
}

resource "google_monitoring_alert_policy" "silence" {
  for_each             = local.silence
  project              = var.project_id
  display_name         = "Sisacao - Silêncio ${each.key}"
  combiner             = "OR"
  notification_channels = var.notification_channels

  documentation {
    content  = local.documentation
    mime_type = "text/markdown"
  }

  alert_strategy {
    notification_rate_limit {
      period = "900s"
    }
  }

  conditions {
    display_name = "silence_${each.key}"
    condition_absent {
      filter = "metric.type=\"logging.googleapis.com/user/sisacao_job_ok\" AND metric.label.\\"job_name\\"=\"${each.key}\""
      duration = "${each.value}s"
      trigger {
        count = 1
      }
    }
  }
}
