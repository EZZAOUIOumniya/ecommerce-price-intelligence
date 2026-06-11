from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from google.cloud import bigquery, bigtable
from airflow.utils.log.logging_mixin import LoggingMixin
import json

logger = LoggingMixin().log

FILE_PATH = "/app/data/cleaned_data.csv"
TRANSFORMED_PATH = "/app/data/transformed.csv"
POSTGRES_CONN = "postgresql+psycopg2://airflow:airflow@postgres:5432/price_db"

BQ_PROJECT = "lyrical-lyceum-499123-c2"
BQ_DATASET = "price_intelligence"
BQ_TABLE = "products"

BT_INSTANCE = "price-intelligence"
BT_TABLE = "price_time_series"


# ─────────────────────────────────────────────
# 1. VALIDATION
# ─────────────────────────────────────────────
def validate_data():
    df = pd.read_csv(FILE_PATH)
    logger.info(f"Rows loaded: {len(df)}")
    if df.empty:
        raise ValueError("Dataset vide")
    zero_price = (df["price"] == 0).sum()
    unknown_source = (df["site"] == "unknown").sum()
    logger.warning(f"Zero price rows: {zero_price}")
    logger.warning(f"Unknown source rows: {unknown_source}")
    if zero_price > len(df) * 0.3:
        raise ValueError("Too many invalid prices (>30%)")
    required_cols = {"row_key", "site", "product_slug", "name", "price",
                     "brand", "category", "url", "scraped_at"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes : {missing}")
    logger.info("Validation OK")


# ─────────────────────────────────────────────
# 2. SUMMARY
# ─────────────────────────────────────────────
def log_summary():
    df = pd.read_csv(FILE_PATH)
    summary = {
        "rows": len(df),
        "sources": df["site"].nunique(),
        "categories": df["category"].nunique(),
        "brands": df["brand"].nunique(),
        "avg_price": round(float(df["price"].mean()), 2),
        "min_price": float(df["price"].min()),
        "max_price": float(df["price"].max()),
        "std_price": round(float(df["price"].std()), 2),
    }
    logger.info(f"Pipeline Summary: {summary}")
    for site, grp in df.groupby("site"):
        logger.info(
            f"  [{site}] {len(grp)} produits | "
            f"avg={round(grp['price'].mean(), 0)} MAD"
        )


# ─────────────────────────────────────────────
# 3. TRANSFORM
# ─────────────────────────────────────────────
def transform_data():
    df = pd.read_csv(FILE_PATH)

    # Renommer row_key → product_id
    df = df.rename(columns={"row_key": "product_id"})

    # Remplacer brand vide
    df["brand"] = df["brand"].fillna("Inconnue")

    # Stats de prix
    df["price_zscore"] = (df["price"] - df["price"].mean()) / df["price"].std()
    df["is_outlier"] = df["price_zscore"].abs() > 3

    category_avg = df.groupby("category")["price"].transform("mean")
    df["price_deviation"] = df["price"] - category_avg
    df["category_avg_price"] = category_avg

    # price_rank par catégorie (dense rank, prix croissant)
    df["price_rank"] = (
        df.groupby("category")["price"]
        .rank(method="dense", ascending=True)
        .astype(int)
    )

    # Garder uniquement les colonnes utiles
    cols = [
        "product_id", "name", "brand", "category", "site",
        "price", "url", "scraped_at",
        "category_avg_price", "price_deviation",
        "price_rank", "price_zscore", "is_outlier",
    ]
    df = df[cols]

    df.to_csv(TRANSFORMED_PATH, index=False)
    logger.info(f"Transformation done — {len(df)} rows written to {TRANSFORMED_PATH}")


# ─────────────────────────────────────────────
# 4. LOAD → POSTGRESQL
# ─────────────────────────────────────────────
def load_to_postgres():
    df = pd.read_csv(TRANSFORMED_PATH)
    engine = create_engine(POSTGRES_CONN)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE public.products"))
    df.to_sql(
        name="products",
        con=engine,
        schema="public",
        if_exists="append",
        index=False,
        method="multi",
        chunksize=500,
    )
    logger.info(f"Loaded {len(df)} rows into PostgreSQL public.products")


# ─────────────────────────────────────────────
# 5. LOAD → BIGQUERY
# ─────────────────────────────────────────────
def load_to_bigquery():
    df = pd.read_csv(TRANSFORMED_PATH)
    df["is_outlier"] = df["is_outlier"].astype(bool)
    df["scraped_at"] = pd.to_datetime(df["scraped_at"])

    client = bigquery.Client(project=BQ_PROJECT)
    table_ref = f"{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}"

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=[
            bigquery.SchemaField("product_id", "STRING"),
            bigquery.SchemaField("name", "STRING"),
            bigquery.SchemaField("brand", "STRING"),
            bigquery.SchemaField("category", "STRING"),
            bigquery.SchemaField("site", "STRING"),
            bigquery.SchemaField("price", "INTEGER"),
            bigquery.SchemaField("url", "STRING"),
            bigquery.SchemaField("scraped_at", "TIMESTAMP"),
            bigquery.SchemaField("category_avg_price", "FLOAT"),
            bigquery.SchemaField("price_deviation", "FLOAT"),
            bigquery.SchemaField("price_rank", "INTEGER"),
            bigquery.SchemaField("price_zscore", "FLOAT"),
            bigquery.SchemaField("is_outlier", "BOOLEAN"),
        ],
    )

    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()
    logger.info(f"Loaded {len(df)} rows into BigQuery {table_ref}")


# ─────────────────────────────────────────────
# 6. LOAD → BIGTABLE  (time-series store)
# ─────────────────────────────────────────────
def load_to_bigtable():
    """
    Écrit chaque ligne dans Bigtable avec la structure :
      row_key  : {product_id}#{scraped_at_iso}
      famille  : price_cf   → price, price_zscore, is_outlier
      famille  : metadata_cf → name, brand, category, site, url
      famille  : agg_cf     → category_avg_price, price_deviation, price_rank
    """
    df = pd.read_csv(TRANSFORMED_PATH)
    df["scraped_at"] = pd.to_datetime(df["scraped_at"])

    bt_client = bigtable.Client(project=BQ_PROJECT, admin=False)
    instance = bt_client.instance(BT_INSTANCE)
    table = instance.table(BT_TABLE)

    rows = []
    for _, row in df.iterrows():
        ts_str = row["scraped_at"].strftime("%Y%m%dT%H%M%S")
        rk = f"{row['product_id']}#{ts_str}".encode()
        bt_row = table.direct_row(rk)

        # price_cf
        bt_row.set_cell("price_cf", "price",
                        str(int(row["price"])).encode())
        bt_row.set_cell("price_cf", "price_zscore",
                        str(round(float(row["price_zscore"]), 4)).encode())
        bt_row.set_cell("price_cf", "is_outlier",
                        str(bool(row["is_outlier"])).encode())

        # metadata_cf
        for col in ["name", "brand", "category", "site", "url"]:
            bt_row.set_cell("metadata_cf", col,
                            str(row[col]).encode())

        # agg_cf
        bt_row.set_cell("agg_cf", "category_avg_price",
                        str(round(float(row["category_avg_price"]), 2)).encode())
        bt_row.set_cell("agg_cf", "price_deviation",
                        str(round(float(row["price_deviation"]), 2)).encode())
        bt_row.set_cell("agg_cf", "price_rank",
                        str(int(row["price_rank"])).encode())

        rows.append(bt_row)

        # flush par batch de 500
        if len(rows) >= 500:
            table.mutate_rows(rows)
            rows = []

    if rows:
        table.mutate_rows(rows)

    logger.info(f"Loaded {len(df)} rows into Bigtable {BT_INSTANCE}/{BT_TABLE}")

def export_stats_for_fullstack():
    df = pd.read_csv(TRANSFORMED_PATH)
    df = df.drop_duplicates(subset=["name", "price", "site"])

    # Stats par catégorie
    stats_cat = df.groupby("category")["price"].agg(
        count="count",
        mean="mean",
        median="median",
        std="std",
        min="min",
        max="max"
    ).round(2).reset_index()

    # Stats par site
    stats_site = df.groupby("site")["price"].agg(
        count="count",
        mean="mean",
        median="median",
        std="std",
        min="min",
        max="max"
    ).round(2).reset_index()

    # Top 10 marques
    top_brands = df[df["brand"] != "INCONNUE"]["brand"].value_counts().head(10)

    # Outliers
    outliers = df[df["is_outlier"]][
        ["name", "brand", "category", "site", "price", "price_zscore"]
    ].sort_values("price", ascending=False).head(20)

    # Heatmap data
    heatmap = df.groupby(["category", "site"])["price"].median().unstack(fill_value=0).round(2)

    result = {
        "summary": {
            "total_products": int(len(df)),
            "sites": df["site"].unique().tolist(),
            "categories": df["category"].nunique(),
            "brands": df["brand"].nunique(),
            "avg_price": round(float(df["price"].mean()), 2),
            "min_price": float(df["price"].min()),
            "max_price": float(df["price"].max()),
            "most_expensive_category": df.groupby("category")["price"].median().idxmax(),
            "cheapest_category": df.groupby("category")["price"].median().idxmin(),
        },
        "stats_by_category": stats_cat.to_dict(orient="records"),
        "stats_by_site": stats_site.to_dict(orient="records"),
        "top_brands": top_brands.reset_index().rename(
            columns={"index": "brand", "brand": "brand", "count": "count"}
        ).to_dict(orient="records"),
        "outliers": outliers.to_dict(orient="records"),
        "heatmap": heatmap.to_dict(),
    }

    output_path = "/app/data/stats_for_fullstack.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info(f"Stats exported to {output_path}")

# ─────────────────────────────────────────────
# DAG DEFINITION
# ─────────────────────────────────────────────
with DAG(
    dag_id="price_data_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["price", "etl", "bigquery", "bigtable"],
) as dag:

    validate_task = PythonOperator(
        task_id="validate_dataset",
        python_callable=validate_data,
    )
    summary_task = PythonOperator(
        task_id="generate_summary",
        python_callable=log_summary,
    )
    transform_task = PythonOperator(
        task_id="transform_data",
        python_callable=transform_data,
    )
    load_pg_task = PythonOperator(
        task_id="load_to_postgres",
        python_callable=load_to_postgres,
    )
    load_bq_task = PythonOperator(
        task_id="load_to_bigquery",
        python_callable=load_to_bigquery,
    )
    load_bt_task = PythonOperator(
        task_id="load_to_bigtable",
        python_callable=load_to_bigtable,
    )
    export_stats_task = PythonOperator(
        task_id="export_stats_for_fullstack",
        python_callable=export_stats_for_fullstack,
    )

    # validate → summary → transform → [postgres, bigquery, bigtable] en parallèle
    validate_task >> summary_task >> transform_task 
    transform_task >> [load_pg_task,
                       load_bq_task,
                       load_bt_task,
                       export_stats_task,
                       ]