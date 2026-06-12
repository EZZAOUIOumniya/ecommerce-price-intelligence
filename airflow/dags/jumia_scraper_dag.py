from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup
from datetime import datetime, timedelta

default_args = {
    'owner': 'abdel',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

SITES = [
    'jumia',
    'iris',
    'electroplanet',
    'uno',
    'micromagma',
    'cosmos_tech',
    'ultrapc',
]

SCRAPY_BIN = '/home/airflow/.local/bin/scrapy'
PROJECT_DIR = '/opt/airflow/scrapers/market_bot'
DATA_DIR = '/opt/airflow/scrapers/market_bot/data'

with DAG(
    'market_intelligence_platform',
    default_args=default_args,
    description = 'High-Performance Parallel Scraping (Kafka Integration)',
    schedule_interval='0 3 * * *',
    start_date = datetime(2026, 4, 21),
    catchup = False,
    is_paused_upon_creation = True,
    tags = ['high_performance', 'scraping', 'kafka'],
) as dag:

    with TaskGroup("parallel_scraping") as scraping_group:
        for site in SITES:
            output_file = f'{DATA_DIR}/{site}_{{{{ ds }}}}.jsonl'

            cmd = (
                f'mkdir -p {DATA_DIR} && '
                f'cd {PROJECT_DIR} && '
                f'PYTHONPATH = {PROJECT_DIR} '
                f'SCRAPY_SETTINGS_MODULE = market_bot.settings '
                f'{SCRAPY_BIN} crawl {site} '
                f'-s LOG_LEVEL = INFO '
                f'-o {output_file}'
            )

            BashOperator(
                task_id = f'scrape_{site}',
                bash_command = cmd,
                env = {
                    'KAFKA_BOOTSTRAP_SERVERS': 'kafka:29092',
                    'KAFKA_TOPIC': 'market_data',
                    'PYTHONPATH': PROJECT_DIR,
                    'SCRAPY_SETTINGS_MODULE': 'market_bot.settings',
                    'PATH': '/home/airflow/.local/bin:/usr/local/bin:/usr/bin:/bin',
                    'HOME': '/home/airflow',
                },
                append_env = True,
                execution_timeout = timedelta(hours = 2),
                do_xcom_push = True,
            )

    scraping_group
