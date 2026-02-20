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

module "notification_channels" {
  source     = "./modules/notification_channels"
  project_id = var.project_id
  email      = var.email
  webhook_url = var.webhook_url
}

module "alert_policies" {
  source                 = "./modules/alert_policies"
  project_id             = var.project_id
  notification_channels  = module.notification_channels.channel_ids
  silence_windows        = var.silence_windows
}
