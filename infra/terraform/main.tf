terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ---------------------------------------------------------------------------
# Cloud Run — Backend API
# ---------------------------------------------------------------------------

resource "google_cloud_run_v2_service" "pilot_backend" {
  name     = "pilot-backend"
  location = var.region

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/pilot/backend:latest"

      ports {
        container_port = 8080
      }

      env {
        name  = "GOOGLE_API_KEY"
        value = var.gemini_api_key
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "1Gi"
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

    timeout = "300s"
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# Allow unauthenticated access (for extension WebSocket)
resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.pilot_backend.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ---------------------------------------------------------------------------
# Artifact Registry — Docker images
# ---------------------------------------------------------------------------

resource "google_artifact_registry_repository" "pilot" {
  location      = var.region
  repository_id = "pilot"
  format        = "DOCKER"
  description   = "Pilot Docker images"
}

# ---------------------------------------------------------------------------
# Firestore — Session storage (production)
# ---------------------------------------------------------------------------

resource "google_firestore_database" "pilot" {
  name        = "pilot-db"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
}

# ---------------------------------------------------------------------------
# Cloud Storage — Screenshot buffer
# ---------------------------------------------------------------------------

resource "google_storage_bucket" "screenshots" {
  name          = "${var.project_id}-pilot-screenshots"
  location      = var.region
  force_destroy = true

  lifecycle_rule {
    condition {
      age = 1  # Auto-delete after 1 day
    }
    action {
      type = "Delete"
    }
  }
}
