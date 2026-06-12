<div align="center">

# 🛒 E-commerce Price Intelligence Platform

> 🎥 **[Voir la vidéo de démonstration (3 min)](https://drive.google.com/file/d/10yawaOQKosvffT9rtsFCoWk2xBi9l5CV/view?usp=sharing)**

> Hybrid Batch + Streaming Data Pipeline — Real-Time Price Monitoring & Analytics()


**A full-stack data engineering solution for real-time price monitoring and analysis across Moroccan e-commerce platforms.**

[![CI](https://github.com/EZZAOUIOumniya/ecommerce-price-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/EZZAOUIOumniya/ecommerce-price-intelligence/actions)
![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![Airflow](https://img.shields.io/badge/Apache%20Airflow-2.9.0-017CEE?logo=apacheairflow&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-1.x-FF694B?logo=dbt&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![GCP](https://img.shields.io/badge/Google%20Cloud-europe--west1-4285F4?logo=googlecloud&logoColor=white)
![License](https://img.shields.io/badge/License-Academic-lightgrey)

<br/>

> Academic project — Pr. ELAACHAK — 2025/2026

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Data Pipeline](#-data-pipeline)
- [Getting Started](#-getting-started)
- [Dashboard](#-dashboard)
- [Cloud Infrastructure (GCP)](#-cloud-infrastructure-gcp)
- [CI/CD](#-cicd)
- [Team](#-team)

---

## 🔍 Overview

The **E-Commerce Price Intelligence Platform** is an end-to-end data pipeline that automatically collects, processes, and visualizes product prices from major Moroccan e-commerce websites — **Jumia**, **Electro**, **Iris**, and **Cosmos Tech**.

The system enables price trend analysis, cross-platform comparisons, anomaly detection, and statistical inference, all through a live interactive dashboard.

**Key capabilities:**

- Automated web scraping with rotating user agents and anti-bot middleware
- Real-time data streaming via Apache NiFi
- Batch orchestration with a 7-task Apache Airflow DAG
- Dual storage strategy: PostgreSQL (local) + BigQuery & Bigtable (cloud)
- Statistical analysis: descriptive stats, hypothesis testing (Kruskal-Wallis), OLS regression
- Live dashboard with price alerts, filters, and interactive charts

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          DATA SOURCES                                │
│         Jumia · Electro · Iris · Cosmos Tech (Scrapy spiders)        │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ raw HTML
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        INGESTION LAYER                               │
│                      Apache NiFi (streaming)                         │
│              Flow: Fetch → Parse → Route → Store                     │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ cleaned_data.csv
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION LAYER                              │
│                   Apache Airflow DAG (batch)                         │
│                                                                      │
│  validate_dataset → generate_summary → transform_data                │
│       → load_to_postgres → load_to_bigquery                          │
│       → load_to_bigtable → export_stats_for_fullstack                │
└──────────────┬──────────────────────────────┬────────────────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────┐        ┌─────────────────────────────────────┐
│  LOCAL STORAGE       │        │  CLOUD STORAGE (GCP)                │
│  PostgreSQL 15       │        │  BigQuery  ──  price_intelligence   │
│  (price_db)          │        │  Bigtable  ──  price_time_series    │
└──────────────────────┘        │  GCS       ──  price-data bucket    │
                                └─────────────────────────────────────┘
                                               │
                                               ▼
                                ┌─────────────────────────────────────┐
                                │  TRANSFORMATION LAYER (dbt)         │
                                │  staging → cleaned → aggregated     │
                                │  → marts (by category, by site)     │
                                └──────────────────┬──────────────────┘
                                                   │
                                                   ▼
                                ┌─────────────────────────────────────┐
                                │  ANALYTICS & VISUALIZATION          │
                                │  Streamlit Dashboard + Plotly       │
                                │  Statistical Analysis (SciPy)       │
                                └─────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Tools & Technologies |
|---|---|
| **Web Scraping** | Scrapy 2.x, BeautifulSoup4, Selenium |
| **Data Streaming** | Apache NiFi |
| **Batch Orchestration** | Apache Airflow 2.9.0 |
| **Data Transformation** | dbt (staging, cleaned, aggregated, marts) |
| **Local Storage** | PostgreSQL 15 |
| **Cloud Storage** | Google Cloud BigQuery, Bigtable, GCS |
| **Analytics** | Python, Pandas, NumPy, SciPy, statsmodels |
| **Visualization** | Plotly, Streamlit |
| **Monitoring** | Prometheus, Grafana |
| **Infrastructure** | Docker, Docker Compose, Terraform |
| **CI/CD** | GitHub Actions |
| **Cloud Provider** | Google Cloud Platform — `europe-west1` |

---

## 🗂️ Project Structure

```
ecommerce-price-intelligence/
│
├── .github/
│   └── workflows/
│       └── ci.yml                        # CI pipeline (lint + dbt check)
│
├── airflow/
│   └── dags/
│       ├── price_pipeline.py             # Main DAG — 7 sequential tasks
│       └── jumia_scraper_dag.py          # Scraping DAG
│
├── charts/                               # Pre-generated analysis charts
│   ├── boxplot_prix_sites.png
│   ├── distribution_prix_categories.png
│   ├── heatmap_prix.png
│   ├── regression_prix_rank.png
│   └── top_marques.png
│
├── data/
│   ├── cleaned_data.csv                  # Ingested & cleaned data (pipeline input)
│   ├── transformed.csv                   # Enriched data (pipeline output)
│   └── stats_for_fullstack.json          # Aggregated stats for the dashboard
│
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/
│       ├── staging/
│       │   ├── stg_prices.sql
│       │   └── stg_products.sql
│       ├── cleaned/
│       │   └── cleaned_prices.sql
│       ├── aggregated/
│       │   ├── agg_daily_prices.sql
│       │   └── agg_price_comparison.sql
│       ├── marts/
│       │   ├── mart_price_by_category.sql
│       │   └── mart_price_by_site.sql
│       └── schema.yml
│
├── docker/
│   ├── docker-compose.yml                # PostgreSQL + Airflow + NiFi
│   ├── Dockerfile
│   ├── data-ingestion/
│   │   ├── Dockerfile.airflow-scraping
│   │   ├── Dockerfile.nifi
│   │   └── docker-compose.yml
│   └── data_fullstack/
│       ├── Dockerfile
│       └── docker-compose.yml
│
├── docs/
│   └── architecture.md
│
├── fullstack/
│   └── app.py                            # Streamlit dashboard
│
├── monitoring/
│   ├── docker-compose.monitoring.yml     # Prometheus + Grafana
│   └── prometheus.yml
│
├── nifi/
│   └── flows/
│       └── price_ingestion_flow.json     # NiFi flow definition
│
├── notebooks/
│   └── analyse_prix.ipynb                # Exploratory data analysis
│
├── scrapers/
│   └── market_bot/
│       └── market_bot/
│           ├── items.py
│           ├── middlewares.py
│           ├── pipelines.py
│           ├── settings.py
│           └── spiders/
│               ├── base_spider.py
│               ├── jumia_spider.py
│               ├── electro_spider.py
│               ├── iris_spider.py
│               └── cosmos_tech.py
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 📊 Data Pipeline

### Airflow DAG — `price_data_pipeline`

The batch pipeline is orchestrated by Airflow and runs 7 tasks sequentially. Any task failure halts the pipeline to preserve data integrity.

```
validate_dataset
      │
      ▼
generate_summary
      │
      ▼
transform_data
      │
      ▼
load_to_postgres
      │
      ▼
load_to_bigquery
      │
      ▼
load_to_bigtable
      │
      ▼
export_stats_for_fullstack
```

| Task | Description |
|---|---|
| `validate_dataset` | Schema validation, null checks, price integrity (rejects if >30% zero-price rows) |
| `generate_summary` | Computes dataset-level stats (row count, source count, avg/min/max price) |
| `transform_data` | Adds z-score, outlier flag, category average, price deviation, and dense rank |
| `load_to_postgres` | Upserts records into `price_db` PostgreSQL instance |
| `load_to_bigquery` | Streams records to the `products` table in BigQuery |
| `load_to_bigtable` | Writes time-series records to Bigtable using composite row key |
| `export_stats_for_fullstack` | Dumps aggregated JSON stats for the Streamlit dashboard |

---

### Input Schema — `cleaned_data.csv`

| Column | Type | Description |
|---|---|---|
| `row_key` | STRING | Unique product identifier |
| `site` | STRING | Source platform (jumia, electro, iris, cosmos) |
| `name` | STRING | Product name |
| `price` | INTEGER | Price in MAD |
| `brand` | STRING | Brand name |
| `category` | STRING | Product category |
| `url` | STRING | Product page URL |
| `scraped_at` | TIMESTAMP | Timestamp of scrape |

### Output Schema — `transformed.csv` (additional columns)

| Column | Description |
|---|---|
| `price_zscore` | Z-score normalization within category |
| `is_outlier` | `True` if `\|z-score\| > 3` |
| `price_deviation` | Absolute deviation from category average |
| `category_avg_price` | Mean price per category |
| `price_rank` | Dense rank within category (ascending price) |

---

### dbt Models

```
staging/
  stg_prices.sql        ← raw prices, type casting
  stg_products.sql      ← raw product metadata

cleaned/
  cleaned_prices.sql    ← deduplication, null handling

aggregated/
  agg_daily_prices.sql        ← daily averages per site/category
  agg_price_comparison.sql    ← cross-platform price comparison

marts/
  mart_price_by_category.sql  ← final model for category analytics
  mart_price_by_site.sql      ← final model for site-level analytics
```

---

## 🚀 Getting Started

### Prerequisites

| Requirement | Version |
|---|---|
| Docker + Docker Compose | latest |
| Python | 3.11+ |
| Google Cloud SDK (`gcloud`) | latest |
| Terraform | >= 1.5 |

---

### Step 1 — Clone the repository

```bash
git clone https://github.com/EZZAOUIOumniya/ecommerce-price-intelligence.git
cd ecommerce-price-intelligence
```

### Step 2 — Configure GCP credentials

```bash
gcloud auth login
gcloud config set project lyrical-lyceum-499123-c2
gcloud auth application-default login
```

### Step 3 — Provision GCP infrastructure with Terraform

```bash
cd terraform
terraform init
terraform plan        # review changes before applying
terraform apply
```

This provisions: BigQuery dataset, Bigtable instance, GCS bucket, and IAM bindings.

### Step 4 — Start the local pipeline stack

```bash
cd docker
docker compose up --build
```

| Service | URL | Credentials |
|---|---|---|
| Airflow UI | http://localhost:8080 | `admin` / `admin123` |
| NiFi UI | http://localhost:8443 | — |
| PostgreSQL | localhost:5432 | `airflow` / `airflow` |

### Step 5 — Trigger the DAG

In the Airflow UI, activate and manually trigger the `price_data_pipeline` DAG. Monitor task execution in the Graph or Grid view.

### Step 6 — Launch the dashboard

```bash
pip install -r requirements.txt
streamlit run fullstack/app.py
```

Dashboard available at → **http://localhost:8501**

### Step 7 — Start monitoring _(optional)_

```bash
cd monitoring
docker compose -f docker-compose.monitoring.yml up
```

| Service | URL | Credentials |
|---|---|---|
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3000 | `admin` / `admin` |

---

## 📈 Dashboard

The Streamlit dashboard provides a real-time view of the price intelligence data across four main sections:

**KPI Overview** — Total products tracked, average price in MAD, active platforms, and live price alert count.

**Price Monitoring** — Time-series trends by platform, category price distribution histograms, price volatility heatmap (category × day), and top price movers.

**Cross-Platform Comparison** — Box plots comparing price ranges per site, with outlier detection.

**Inferential Statistics** — Three analytical tabs:
- *Descriptive Stats*: mean, median, std dev, IQR per category
- *Hypothesis Tests*: Kruskal-Wallis test to determine whether price distributions differ significantly across platforms
- *Regression*: OLS model — `price ~ rating + reviews + log(reviews)` — with coefficient table and residual plot

**Filters** — The sidebar allows filtering by product category and platform; all charts update dynamically.

---

## ☁️ Cloud Infrastructure (GCP)

### Provisioned Resources

| Resource | Name |
|---|---|
| GCP Project | `lyrical-lyceum-499123-c2` |
| Region | `europe-west1` |
| BigQuery Dataset | `price_intelligence` |
| BigQuery Table | `products` |
| Bigtable Instance | `price-intelligence` |
| Bigtable Table | `price_time_series` |
| GCS Bucket | `lyrical-lyceum-499123-c2-price-data` |

### Bigtable Row Key Design

```
{product_id}#{scraped_at}
```

| Column Family | Columns |
|---|---|
| `price_cf` | `price`, `price_zscore`, `is_outlier` |
| `metadata_cf` | `name`, `brand`, `category`, `site`, `url` |
| `agg_cf` | `category_avg_price`, `price_deviation`, `price_rank` |

The composite row key enables efficient time-range scans per product while keeping related price metrics co-located in the same row.

---

## 🧪 CI/CD

GitHub Actions runs automatically on every push to `main`:

```yaml
Jobs:
  lint-and-test
    ├── flake8 linting (Python source files)
    └── validate_data.py script execution

  dbt-check
    └── dbt parse (syntax validation of all SQL models)
```

All jobs must pass before a pull request can be merged.

---

## 👥 Team

| Role | Responsibilities |
|---|---|
| **DevOps Engineer** | Docker Compose, Airflow setup, NiFi flows, PostgreSQL, GCP provisioning (Terraform), CI/CD |
| **Data Engineer** | Scrapy spiders, NiFi pipeline configuration, data cleaning & validation |
| **Data Analyst** | Statistical analysis (SciPy, statsmodels), Jupyter notebooks, chart generation |
| **Full Stack Developer** | Streamlit dashboard, Plotly visualizations, JSON API for stats |

---

## 📄 License

This project was developed for academic purposes under the supervision of **Pr. ELAACHAK** — academic year **2025/2026**. All rights reserved.