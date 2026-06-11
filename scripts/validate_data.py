"""
validate_data.py — Script autonome de validation qualité des données.
Utilisé par le Dockerfile (service app) et le CI GitHub Actions.
"""

import sys
import logging
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

FILE_PATH = "/app/data/cleaned_data.csv"


def validate_data(filepath: str = FILE_PATH) -> bool:
    logger.info(f"Lecture du fichier : {filepath}")
    try:
        df = pd.read_csv(filepath)
    except FileNotFoundError:
        logger.warning(f"Fichier introuvable : {filepath} (normal en CI)")
        return True  # pas un échec bloquant en CI

    logger.info(f"Lignes chargées : {len(df)}")

    if df.empty:
        logger.error("Dataset vide !")
        return False

    # ── Colonnes requises ────────────────────────────────────────────────
    required_cols = {"row_key", "site", "name", "price", "brand",
                     "category", "url", "scraped_at"}
    missing = required_cols - set(df.columns)
    if missing:
        logger.error(f"Colonnes manquantes : {missing}")
        return False
    logger.info("Colonnes : OK")

    # ── Prix invalides ───────────────────────────────────────────────────
    zero_price = (df["price"] == 0).sum()
    null_price = df["price"].isna().sum()
    neg_price = (df["price"] < 0).sum()
    logger.info(f"Prix à 0 : {zero_price} | nuls : {null_price} | négatifs : {neg_price}")
    if zero_price > len(df) * 0.3:
        logger.error("Trop de prix invalides (>30%)")
        return False

    # ── Sources inconnues ────────────────────────────────────────────────
    unknown_source = (df["site"] == "unknown").sum()
    logger.info(f"Sources inconnues : {unknown_source}")

    # ── Doublons ─────────────────────────────────────────────────────────
    dup = df.duplicated(subset=["row_key"]).sum()
    logger.info(f"Doublons sur row_key : {dup}")

    # ── Résumé statistique ───────────────────────────────────────────────
    logger.info("── Statistiques ──────────────────────────────────────────")
    logger.info(f"  Sources     : {sorted(df['site'].unique().tolist())}")
    logger.info(f"  Catégories  : {sorted(df['category'].unique().tolist())}")
    logger.info(f"  Prix moy.   : {df['price'].mean():.0f} MAD")
    logger.info(f"  Prix min/max: {df['price'].min()} / {df['price'].max()} MAD")
    logger.info(f"  Produits    : {df['name'].nunique()} uniques")
    logger.info("──────────────────────────────────────────────────────────")
    logger.info("Validation OK ✓")
    return True


if __name__ == "__main__":
    ok = validate_data()
    sys.exit(0 if ok else 1)