output "bigquery_table" {
  value = "${var.project_id}.${google_bigquery_dataset.price_intelligence.dataset_id}.${google_bigquery_table.products.table_id}"
}

output "bigtable_instance" {
  value = google_bigtable_instance.price_intelligence.name
}

output "service_account_email" {
  value = google_service_account.airflow_sa.email
}