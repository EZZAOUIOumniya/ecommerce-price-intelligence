import sys
import json
import os
import time
import warnings
import re
from google.cloud import bigtable

warnings.filterwarnings("ignore", category=FutureWarning)

# ✅ REMOVED: os.environ["BIGTABLE_EMULATOR_HOST"] = "bigtable:8086"
# ✅ Read real GCP values from environment (set in docker-compose via .env)
PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "lyrical-lyceum-499123-c2")
INSTANCE_ID = os.environ.get("BIGTABLE_INSTANCE_ID", "price-intel")

BATCH_SIZE = 500  # ✅ Real Bigtable supports larger batches (was 200 for emulator)
MAX_RETRIES = 3


# ------------------------------------------------------------------ #
#  Price cleaner                                                       #
# ------------------------------------------------------------------ #

def clean_price_value(value) -> str:
    """
    Convertit n'importe quel format de prix en string entier propre.

    Exemples :
      5899          (int)   -> "5899"
      5899.0        (float) -> "5899"
      "5899.00"     (str)   -> "5899"
      "5,899.00"    (str)   -> "5899"  virgule = séparateur milliers
      "5 899,00"    (str)   -> "5899"  format européen
      "5.899,00"    (str)   -> "5899"  format européen avec point milliers
      None / ""             -> "0"
    """
    if value is None:
        return "0"

    if isinstance(value, (int, float)):
        return str(int(value))

    price_str = str(value).strip()

    if ',' in price_str and '.' in price_str:
        if price_str.rindex(',') > price_str.rindex('.'):
            price_str = price_str.replace('.', '').replace(',', '.')
        else:
            price_str = price_str.replace(',', '')
    elif ',' in price_str:
        parts = price_str.split(',')
        if len(parts) == 2 and len(parts[1]) <= 2:
            price_str = price_str.replace(',', '.')
        else:
            price_str = price_str.replace(',', '')

    price_str = price_str.split('.')[0]
    digits = re.sub(r'[^\d]', '', price_str)

    return digits if digits else "0"


# ------------------------------------------------------------------ #
#  Source resolver                                                     #
# ------------------------------------------------------------------ #

def get_source(item) -> str:
    raw_source = str(item.get('site') or item.get('source') or 'unknown').lower()
    source = re.sub(r"[^a-z0-9]", "", raw_source)

    if source == 'unknown':
        url = str(item.get('url', '')).lower()
        if 'jumia.ma' in url:
            source = 'jumia'
        elif 'electroplanet.ma' in url:
            source = 'electroplanet'
        elif 'uno.ma' in url:
            source = 'uno'
        elif 'iris.ma' in url:
            source = 'iris'

    return source


# ------------------------------------------------------------------ #
#  Row builder                                                         #
# ------------------------------------------------------------------ #

def build_row(table, item, source):
    # ✅ supports both 'product_id' (your data) and 'id' (generic)
    item_id = re.sub(r"[^a-z0-9_-]", "_", str(item.get('product_id') or item.get('id', 'unknown')))
    raw_date = str(item.get('scraped_at', '0000'))
    scraped_at = raw_date.replace(" ", "T").replace(":", "-")

    row_key = f"{source}#{item_id}#{scraped_at}".encode()
    row = table.direct_row(row_key)

    row.set_cell('price_cf', b'site', source.encode())
    row.set_cell('price_cf', b'name', str(item.get('name', 'N/A')).encode())
    row.set_cell('price_cf', b'price', clean_price_value(item.get('price')).encode())
    row.set_cell('price_cf', b'brand', str(item.get('brand', 'Inconnue')).encode())
    row.set_cell('price_cf', b'category', str(item.get('category', 'N/A')).encode())
    row.set_cell('price_cf', b'url', str(item.get('url', '')).lower().encode())
    row.set_cell('price_cf', b'scraped_at', raw_date.encode())

    return row


# ------------------------------------------------------------------ #
#  Batch helpers                                                       #
# ------------------------------------------------------------------ #

def chunked(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def mutate_with_retry(table, batch, max_retries=MAX_RETRIES):
    """Envoie un batch avec retry + exponential backoff."""
    for attempt in range(max_retries):
        try:
            return table.mutate_rows(batch)
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # 1s, 2s, 4s
                sys.stderr.write(
                    f"⚠️ Batch attempt {attempt + 1} failed: {e}. Retrying in {wait}s...\n"
                )
                time.sleep(wait)
            else:
                raise e


# ------------------------------------------------------------------ #
#  Main entrypoint (NiFi compatible)                                  #
# ------------------------------------------------------------------ #

def run():
    """
    Interface NiFi :
      - Lit le JSON depuis stdin (ExecuteStreamCommand)
      - Écrit le summary JSON sur stdout
      - Écrit les erreurs sur stderr
      - Exit 1 en cas d'erreur fatale → NiFi route vers failure
    """
    raw_input = sys.stdin.read()
    if not raw_input or not raw_input.strip():
        sys.stderr.write("⚠️ Empty input received, skipping.\n")
        return

    try:
        data_json = json.loads(raw_input)
        items = data_json if isinstance(data_json, list) else [data_json]

        # ✅ FIXED: use real PROJECT_ID and INSTANCE_ID from environment
        # ✅ REMOVED: admin=True (not needed for writes, reduces required permissions)
        client = bigtable.Client(project=PROJECT_ID)
        instance = client.instance(INSTANCE_ID)
        table = instance.table('price_history')

        rows = [build_row(table, item, get_source(item)) for item in items]

        failed = 0
        for batch in chunked(rows, BATCH_SIZE):
            responses = mutate_with_retry(table, batch)
            for i, response in enumerate(responses):
                if response.code != 0:
                    sys.stderr.write(
                        f"⚠️ Row {i} failed (code {response.code}): {response.message}\n"
                    )
                    failed += 1

        total = len(rows)
        written = total - failed

        sys.stderr.write(f"✅ {written}/{total} rows written to Bigtable"
                         f" (project={PROJECT_ID}, instance = {INSTANCE_ID}).\n")

        summary = json.dumps({
            "written": written,
            "failed": failed,
            "total": total,
            "project": PROJECT_ID,
            "instance": INSTANCE_ID,
        })
        sys.stdout.write(summary)

    except json.JSONDecodeError as e:
        sys.stderr.write(f"❌ JSON PARSE ERROR: {e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"❌ BIGTABLE ERROR: {str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    run()
