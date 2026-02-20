terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
}

locals {
  job_map = { for name in var.job_names : name => replace(name, "_", "-") }
}

resource "google_service_account" "jobs" {
  for_each     = local.job_map
  account_id   = "sa-${each.value}"
  display_name = "Sisacao job ${each.key}"
}

resource "google_service_account" "scheduler" {
  account_id   = var.scheduler_account_id
  display_name = "Sisacao scheduler invoker"
}

resource "google_bigquery_dataset_iam_member" "data_editor" {
  for_each   = google_service_account.jobs
  project    = var.project_id
  dataset_id = var.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${each.value.email}"
}

resource "google_project_iam_member" "job_user" {
  for_each = google_service_account.jobs
  project  = var.project_id
  role     = "roles/bigquery.jobUser"
  member   = "serviceAccount:${each.value.email}"
}

resource "google_project_iam_member" "log_writer" {
  for_each = google_service_account.jobs
  project  = var.project_id
  role     = "roles/logging.logWriter"
  member   = "serviceAccount:${each.value.email}"
}

resource "google_project_iam_member" "scheduler_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.scheduler.email}"
}
