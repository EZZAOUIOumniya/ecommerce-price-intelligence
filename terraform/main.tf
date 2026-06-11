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

resource "google_bigquery_dataset" "price_intelligence" {
  dataset_id  = "price_intelligence"
  location    = "US"
  description = "Dataset principal price intelligence"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_bigquery_table" "products" {
  dataset_id          = google_bigquery_dataset.price_intelligence.dataset_id
  table_id            = "products"
  deletion_protection = false
  schema              = file("${path.module}/schema_products.json")
}

resource "google_bigtable_instance" "price_intelligence" {
  name                = "price-intelligence"
  deletion_protection = false

  cluster {
    cluster_id   = "price-intelligence-cluster"
    zone         = "${var.region}-b"
    num_nodes    = 1
    storage_type = "SSD"
  }
}

resource "google_bigtable_table" "price_time_series" {
  name          = "price_time_series"
  instance_name = google_bigtable_instance.price_intelligence.name

  column_family { family = "price_cf" }
  column_family { family = "metadata_cf" }
  column_family { family = "agg_cf" }
}

resource "google_storage_bucket" "price_data" {
  name          = "${var.project_id}-price-data"
  location      = var.region
  force_destroy = true
  uniform_bucket_level_access = true

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_service_account" "airflow_sa" {
  account_id   = "airflow-sa"
  display_name = "Airflow Service Account"
}

resource "google_project_iam_member" "bq_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.airflow_sa.email}"
}

resource "google_project_iam_member" "bt_editor" {
  project = var.project_id
  role    = "roles/bigtable.user"
  member  = "serviceAccount:${google_service_account.airflow_sa.email}"
}