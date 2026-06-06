from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from airflow.utils.log.logging_mixin import LoggingMixin

logger = LoggingMixin().log

FILE_PATH = "/app/data/cleaned_data.csv"
TRANSFORMED_PATH = "/app/data/transformed.csv"
POSTGRES_CONN = "postgresql+psycopg2://airflow:airflow@postgres:5432/price_db"

# -------------------------
# 1. DATA QUALITY CHECK
# -------------------------
def validate_data():
    df = pd.read_csv(FILE_PATH)
    logger.info(f"Rows: {len(df)}")
    if df.empty:
        raise ValueError("Dataset vide")
    zero_price = (df["price"] == 0).sum()
    unknown_source = (df["site"] == "unknown").sum()
    logger.warning(f"Zero price rows: {zero_price}")
    logger.warning(f"Unknown source rows: {unknown_source}")
    if zero_price > len(df) * 0.3:
        raise ValueError("Too many invalid prices")
    logger.info("Validation OK")

# -------------------------
# 2. SUMMARY
# -------------------------
def log_summary():
    df = pd.read_csv(FILE_PATH)
    summary = {
        "rows": len(df),
        "sources": df["site"].nunique(),
        "avg_price": float(df["price"].mean()),
        "min_price": float(df["price"].min()),
        "max_price": float(df["price"].max()),
    }
    logger.info(f"Summary: {summary}")

# -------------------------
# 3. TRANSFORM
# -------------------------
def transform_data():
    df = pd.read_csv(FILE_PATH)

    # Correction colonnes inversées site/name
    df = df.rename(columns={"site": "name", "name": "site"})

    # Extraire le vrai site depuis product_id (format: site#...)
    df["site"] = df["product_id"].str.split("#").str[0]

    # Remplacer brand vide par "Inconnue"
    df["brand"] = df["brand"].fillna("Inconnue")

    # Calculs stats
    df["price_zscore"] = (df["price"] - df["price"].mean()) / df["price"].std()
    df["is_outlier"] = df["price_zscore"].abs() > 3
    category_avg = df.groupby("category")["price"].transform("mean")
    df["price_deviation"] = df["price"] - category_avg
    df["category_avg_price"] = category_avg

    df.to_csv(TRANSFORMED_PATH, index=False)
    logger.info(f"Transformation done — {len(df)} rows written")


# -------------------------
# 4. LOAD TO POSTGRESQL
# -------------------------
def load_to_postgres():
    df = pd.read_csv(TRANSFORMED_PATH)

    engine = create_engine(POSTGRES_CONN)

    # Vider la table sans la supprimer
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE public.products"))

    # Charger les nouvelles données
    df.to_sql(
        name="products",
        con=engine,
        schema="public",
        if_exists="append",
        index=False,
        method="multi",
        chunksize=500,
    )

    logger.info(
        f"Loaded {len(df)} rows into PostgreSQL table 'public.products'"
    )

# -------------------------
# DAG
# -------------------------
with DAG(
    dag_id="price_data_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["price", "etl"],
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
    load_task = PythonOperator(
        task_id="load_to_postgres",
        python_callable=load_to_postgres,
    )

    validate_task >> summary_task >> transform_task >> load_task