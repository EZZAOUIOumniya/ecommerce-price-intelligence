FROM apache/airflow:2.9.0

USER root

# --- ÉTAPE 1 : DÉPENDANCES SYSTÈME MINIMALES ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git libpq-dev librdkafka-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- ÉTAPE 2 : INSTALLATION DES PACKAGES PYTHON ---
USER airflow
RUN pip install --no-cache-dir \
    playwright scrapy scrapy-playwright confluent-kafka \
    google-cloud-bigtable dbt-core dbt-postgres

# Installe les binaires Chromium (dans /home/airflow/.cache/ms-playwright)
RUN playwright install chromium

# --- ÉTAPE 3 : INSTALLATION DES DÉPENDANCES SYSTÈME RESTANTES (AUTOMATISÉ) ---
USER root
# Utilise la commande officielle qui détecte et installe tout ce qui manque pour Chromium
RUN playwright install-deps chromium

# On s'assure que l'utilisateur airflow est propriétaire de ses dossiers
RUN chown -R airflow: /home/airflow/.cache

USER airflow
