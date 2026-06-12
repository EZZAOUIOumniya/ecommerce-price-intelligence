import json
import os
import logging
from confluent_kafka import Producer


class KafkaPipeline:

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        instance = cls(
            bootstrap_servers=os.environ.get(
                'KAFKA_BOOTSTRAP_SERVERS',
                settings.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
            ),
            topic=os.environ.get(
                'KAFKA_TOPIC',
                settings.get('KAFKA_TOPIC', 'market_data')
            ),
        )
        instance.crawler = crawler
        return instance

    def __init__(self, bootstrap_servers, topic):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.producer = Producer({
            'bootstrap.servers':      self.bootstrap_servers,
            'client.id':              'scrapy-bot',
            'socket.timeout.ms':      10000,
            'queue.buffering.max.ms': 5,
            'enable.idempotence':     True,
            'message.timeout.ms':     30000,
        })
        self.items_produced = 0

    def process_item(self, item):
        try:
            spider = self.crawler.spider
            if 'source' not in item:
                item['source'] = spider.name
            payload = json.dumps(dict(item), default=str)
            self.producer.produce(
                self.topic,
                value=payload.encode('utf-8'),
                callback=self.delivery_report,
            )
            self.items_produced += 1
            if self.items_produced % 10 == 0:
                self.producer.poll(0)
        except Exception as e:
            logging.error(f"❌ Kafka Error: {e}")
        return item

    def delivery_report(self, err, msg):
        if err is not None:
            logging.error(f"❌ Kafka Delivery Failed: {err}")
        else:
            logging.debug(f"✅ Item livré à {msg.topic()} [{msg.partition()}]")

    def close_spider(self):
        spider = self.crawler.spider
        spider.logger.info(
            f"Finalizing Kafka: {self.items_produced} items produced. Flushing..."
        )
        remaining = self.producer.flush(timeout=15)
        if remaining > 0:
            spider.logger.warning(
                f"⚠️ {remaining} messages n'ont pas pu être livrés à Kafka."
            )
        else:
            spider.logger.info("🚀 Tous les messages ont été envoyés avec succès.")
