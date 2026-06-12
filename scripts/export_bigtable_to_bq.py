"""
export_bigtable_to_bq.py
Reads all rows from Bigtable price_history table
and loads them directly into BigQuery as price_history_raw.
"""

import os
from google.cloud import bigtable
from google.cloud import bigquery

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "lyrical-lyceum-499123-c2")
INSTANCE_ID = os.environ.get("BIGTABLE_INSTANCE_ID", "price-intel")
DATASET_ID = "price_intelligence"
TABLE_ID = "price_history_raw"
BATCH_SIZE = 1000  # rows per BigQuery insert

# ------------------------------------------------------------------ #
#  BigQuery schema                                                     #
# ------------------------------------------------------------------ #

SCHEMA = [
    bigquery.SchemaField("row_key", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("price_cf_site", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("price_cf_name", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("price_cf_price", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("price_cf_brand", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("price_cf_category", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("price_cf_url", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("price_cf_scraped_at", "STRING", mode="NULLABLE"),
]

# ------------------------------------------------------------------ #
#  Setup                                                               #
# ------------------------------------------------------------------ #

def get_or_create_bq_table(bq_client):
    dataset_ref = bq_client.dataset(DATASET_ID)

    # Create dataset if not exists
    try:
        bq_client.get_dataset(dataset_ref)
        print(f"✅ Dataset {DATASET_ID} already exists.")
    except Exception:
        dataset = bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}")
        dataset.location = "US"
        bq_client.create_dataset(dataset)
        print(f"✅ Dataset {DATASET_ID} created.")

    # Create table if not exists (truncate if exists)
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    table = bigquery.Table(table_ref, schema=SCHEMA)
    bq_client.delete_table(table_ref, not_found_ok=True)
    bq_client.create_table(table)
    print(f"✅ Table {TABLE_ID} created (fresh).")
    return table_ref


# ------------------------------------------------------------------ #
#  Read Bigtable row → dict                                            #
# ------------------------------------------------------------------ #

def row_to_dict(row):
    def get_cell(family, column):
        try:
            return row.cells[family][column.encode()][0].value.decode("utf-8", errors="replace")
        except (KeyError, IndexError):
            return None

    return {
        "row_key": row.row_key.decode("utf-8", errors="replace"),
        "price_cf_site": get_cell("price_cf", "site"),
        "price_cf_name": get_cell("price_cf", "name"),
        "price_cf_price": get_cell("price_cf", "price"),
        "price_cf_brand": get_cell("price_cf", "brand"),
        "price_cf_category": get_cell("price_cf", "category"),
        "price_cf_url": get_cell("price_cf", "url"),
        "price_cf_scraped_at": get_cell("price_cf", "scraped_at"),
    }


# ------------------------------------------------------------------ #
#  Main                                                                #
# ------------------------------------------------------------------ #

def main():
    print(f"🔗 Connecting to Bigtable: {PROJECT_ID} / {INSTANCE_ID}")
    bt_client = bigtable.Client(project=PROJECT_ID, admin=False)
    instance = bt_client.instance(INSTANCE_ID)
    table = instance.table("price_history")

    print(f"🔗 Connecting to BigQuery: {PROJECT_ID} / {DATASET_ID}")
    bq_client = bigquery.Client(project=PROJECT_ID)
    table_ref = get_or_create_bq_table(bq_client)

    print("📖 Reading rows from Bigtable...")
    rows_read = 0
    rows_written = 0
    batch = []
    errors_total = []

    for row in table.read_rows():
        batch.append(row_to_dict(row))
        rows_read += 1

        if len(batch) >= BATCH_SIZE:
            errors = bq_client.insert_rows_json(table_ref, batch)
            if errors:
                errors_total.extend(errors)
                print(f"⚠️  {len(errors)} insert errors in batch")
            else:
                rows_written += len(batch)
            print(f"   ↳ {rows_read} rows read, {rows_written} written...")
            batch = []

    # flush remaining
    if batch:
        errors = bq_client.insert_rows_json(table_ref, batch)
        if errors:
            errors_total.extend(errors)
        else:
            rows_written += len(batch)

    print(f"\n✅ Done! {rows_written}/{rows_read} rows written to BigQuery.")
    print(f"   Table: {table_ref}")
    if errors_total:
        print(f"⚠️  Total insert errors: {len(errors_total)}")
        for e in errors_total[:5]:
            print(f"{e}")


if __name__ == "__main__":
    main()
