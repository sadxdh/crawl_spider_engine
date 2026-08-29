"""
Kafka 入库 Pipeline（可选，替换 MysqlPipeline）
Priority: 320
通过 custom_settings: ['KafkaPipeline'] 启用
"""
import json
from kafka import KafkaProducer
from scrapy.exceptions import NotConfigured
from loguru import logger
from config import KAFKA_CONF


class KafkaPipeline:
    """Kafka 消息入库"""

    def __init__(self):
        self.producer = None
        self.item_count = 0

    def open_spider(self, spider):
        task = getattr(spider, 'task', {}) or {}
        bootstrap_servers = KAFKA_CONF.get('host', 'localhost:9092')
        self.topic = task.get('kafka_topic') or KAFKA_CONF.get('topic', 'crawl_data')

        try:
            self.producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
                acks='all',
                retries=3,
            )
            logger.info(f"[KafkaPipeline] 初始化: {bootstrap_servers} topic={self.topic}")
        except Exception as e:
            logger.error(f"[KafkaPipeline] 初始化失败: {e}")
            raise NotConfigured(f"Kafka连接失败: {e}")

    def process_item(self, item, spider):
        item_dict = dict(item)
        try:
            self.producer.send(self.topic, value=item_dict)
            self.item_count += 1
            return item
        except Exception as e:
            logger.error(f"[KafkaPipeline] 发送失败: {e}")
            raise

    def close_spider(self, spider):
        if self.producer:
            self.producer.flush()
            self.producer.close()
        logger.info(f"[KafkaPipeline] 关闭: {spider.name} 发送={self.item_count}")
