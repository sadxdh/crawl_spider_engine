"""
MongoDB Pipeline（可选）
Priority: 330
通过 custom_settings: ['MongoDBPipeline'] 启用
"""
import json
from datetime import datetime
import pymongo
from loguru import logger
from scrapy.exceptions import NotConfigured


class MongoDBPipeline:
    """MongoDB 数据入库"""

    def __init__(self):
        self.client = None
        self.db = None
        self.item_count = 0

    def open_spider(self, spider):
        try:
            task = getattr(spider, 'task', {}) or {}
            mongo_uri = task.get('mongo_uri', 'mongodb://localhost:27017/')
            db_name = task.get('mongo_db', 'crawl_data')
            collection_name = task.get('data_table', spider.name)

            self.client = pymongo.MongoClient(mongo_uri)
            self.collection = self.client[db_name][collection_name]
            logger.info(f"[MongoDBPipeline] 连接: {mongo_uri}/{db_name}/{collection_name}")
        except Exception as e:
            raise NotConfigured(f"MongoDB连接失败: {e}")

    def process_item(self, item, spider):
        item_dict = dict(item)
        item_dict['crawl_time'] = datetime.now().isoformat()
        try:
            self.collection.insert_one(item_dict)
            self.item_count += 1
        except Exception as e:
            logger.error(f"[MongoDBPipeline] 写入失败: {e}")
            raise
        return item

    def close_spider(self, spider):
        if self.client:
            self.client.close()
        logger.info(f"[MongoDBPipeline] 关闭: {spider.name} 写入={self.item_count}")
