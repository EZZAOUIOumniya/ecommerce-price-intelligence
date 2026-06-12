---

## 🗂️ Project Structure
ecommerce-price-intelligence/
├── airflow/
│   └── dags/
│       └── price_pipeline.py        # DAG principal (7 tâches)
├── charts/                          # Graphiques générés par le data analyst
├── data/
│   ├── cleaned_data.csv             # Données source (data engineer)
│   ├── transformed.csv              # Données transformées (pipeline output)
│   └── stats_for_fullstack.json     # Stats exportées pour le dashboard
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/
│       ├── staging/stg_products.sql
│       └── marts/
│           ├── mart_price_by_category.sql
│           └── mart_price_by_site.sql
├── docker/
│   ├── docker-compose.yml           # PostgreSQL + Airflow + NiFi
│   └── Dockerfile
├── docs/
│   └── architecture.md
├── monitoring/
│   ├── docker-compose.monitoring.yml
│   └── prometheus.yml
├── nifi/
│   └── flows/
│       └── price_ingestion_flow.json
├── scripts/
│   ├── init_db.sql                  # Schéma PostgreSQL
│   └── validate_data.py
├── terraform/
│   ├── main.tf                      # BigQuery + Bigtable + GCS + IAM
│   ├── variables.tf
│   ├── outputs.tf
│   └── schema_products.json
├── .github/
│   └── workflows/
│       └── ci.yml                   # CI/CD GitHub Actions
├── requirements.txt
└── README.md
├── .gitignore

---

## 🛠️ Technology Stack

| Layer | Tools |
|---|---|
| Scraping | Scrapy, BeautifulSoup, Selenium |
| Streaming | Apache NiFi |
| Batch Orchestration | Apache Airflow 2.9.0 |
| Storage (local) | PostgreSQL 15 |
| Storage (cloud) | Google Cloud Bigtable + BigQuery |
| Transformation | dbt (staging + marts) |
| Analytics | Python, Pandas, SciPy, statsmodels |
| Visualization | Plotly, Streamlit |
| Monitoring | Prometheus + Grafana |
| Infrastructure | Docker, Docker Compose, Terraform |
| CI/CD | GitHub Actions |
| Cloud | Google Cloud Platform (europe-west1) |

---

## 🚀 Getting Started

### Prerequisites

- Docker + Docker Compose
- Python 3.11+
- Google Cloud SDK (`gcloud`)
- Terraform

### 1 — Clone the repo

```bash
git clone https://github.com/EZZAOUIOumniya/ecommerce-price-intelligence.git
cd ecommerce-price-intelligence
```

### 2 — GCP Authentication

```bash
gcloud auth login
gcloud config set project lyrical-lyceum-499123-c2
gcloud auth application-default login
```

### 3 — Deploy GCP Infrastructure

```bash
cd terraform
terraform init
terraform apply
```

### 4 — Start local pipeline

```bash
cd docker
docker compose up --build
```

Airflow UI → `http://localhost:8080` — login: `admin` / `admin123`

### 5 — Trigger the DAG

Dans l'UI Airflow, active et trigger le DAG `price_data_pipeline`.

Les 7 tâches s'exécutent dans cet ordre :
validate_dataset
→ generate_summary
→ transform_data
→ load_to_postgres
→ load_to_bigquery
→ load_to_bigtable
→ export_stats_for_fullstack

### 6 — Start monitoring (optional)

```bash
cd monitoring
docker compose -f docker-compose.monitoring.yml up
```

- Prometheus → `http://localhost:9090`
- Grafana → `http://localhost:3000` — login: `admin` / `admin`

---

## 📊 Data Pipeline

### Input — `cleaned_data.csv`

| Column | Type | Description |
|---|---|---|
| row_key | STRING | Unique product identifier |
| site | STRING | Source website |
| name | STRING | Product name |
| price | INTEGER | Price in MAD |
| brand | STRING | Brand name |
| category | STRING | Product category |
| url | STRING | Product URL |
| scraped_at | TIMESTAMP | Scraping timestamp |

### Output — `transformed.csv`

Additional computed columns:

| Column | Description |
|---|---|
| price_zscore | Z-score normalization |
| is_outlier | True if \|z-score\| > 3 |
| price_deviation | Deviation from category average |
| category_avg_price | Average price per category |
| price_rank | Dense rank within category |

---

## ☁️ GCP Resources

| Resource | Name |
|---|---|
| Project | `lyrical-lyceum-499123-c2` |
| BigQuery Dataset | `price_intelligence` |
| BigQuery Table | `products` |
| Bigtable Instance | `price-intelligence` |
| Bigtable Table | `price_time_series` |
| GCS Bucket | `lyrical-lyceum-499123-c2-price-data` |
| Region | `europe-west1` |

### Bigtable Schema
Row key: {product_id}#{scraped_at}
Column families:
├── price_cf      → price, price_zscore, is_outlier
├── metadata_cf   → name, brand, category, site, url
└── agg_cf        → category_avg_price, price_deviation, price_rank
---

## 🧪 CI/CD

GitHub Actions pipeline runs on every push to `main`:

- ✅ **lint-and-test** — flake8 linting + validate script
- ✅ **dbt-check** — dbt parse syntax check

---

## 👥 Team

| Role | Responsibilities |
|---|---|
| DevOps | Docker, Airflow, NiFi flows, PostgreSQL, GCP, Terraform, CI/CD |
| Data Engineer | Scrapy spiders, NiFi flows, data cleaning |
| Data Analyst | Statistical analysis, charts, insights |
| Full Stack | Dashboard, API, visualization |

---

## 📄 License

Academic project — Pr. ELAACHAK — 2025/2026