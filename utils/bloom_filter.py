"""
布隆过滤器 - 基于 Redis BitMap + mmh3
参考: yuncrawl/crawl/utils/bloom_filter.py
改进: per-spider 独立 Key，支持 TTL 和 reset 标志
"""
import mmh3
import redis
from loguru import logger


class BloomFilter:
    """
    基于 Redis BitMap 的布隆过滤器

    Key格式: crawl_engine:dupefilter:req:{spider_name}
    每个爬虫独立 Key，避免跨爬虫污染（改进自 yuncrawl 固定 Key 方案）

    参数:
        bit=30  -> 2^30 bit = 128MB，约可存 1 亿 URL，误判率 < 0.1%
        hash_number=6 -> 6个哈希函数
    """

    def __init__(self, server: redis.Redis, key: str, bit: int = 30, hash_number: int = 6):
        self.server = server
        self.key = key
        self.m = 1 << bit          # 位数组大小
        self.seeds = list(range(hash_number))
        logger.debug(f"[BloomFilter] key={key}, m={self.m}, hash_number={hash_number}")

    def _get_hash_values(self, value: str) -> list[int]:
        """计算所有哈希值对应的位位置"""
        return [mmh3.hash(value, seed=s, signed=False) % self.m for s in self.seeds]

    def exists(self, value: str) -> bool:
        """检查值是否存在（可能存在假阳性）"""
        with self.server.pipeline() as pipe:
            for offset in self._get_hash_values(value):
                pipe.getbit(self.key, offset)
            return all(pipe.execute())

    def insert(self, value: str):
        """插入值"""
        with self.server.pipeline() as pipe:
            for offset in self._get_hash_values(value):
                pipe.setbit(self.key, offset, 1)
            pipe.execute()

    def reset(self):
        """清空布隆过滤器"""
        self.server.delete(self.key)
        logger.info(f"[BloomFilter] 已清空: {self.key}")

    def set_ttl(self, seconds: int):
        """设置过期时间"""
        self.server.expire(self.key, seconds)


def get_bloom_filter(server: redis.Redis, spider_name: str, **kwargs) -> BloomFilter:
    """
    获取指定爬虫的布隆过滤器
    Key格式: crawl_engine:dupefilter:req:{spider_name}
    """
    key = f'crawl_engine:dupefilter:req:{spider_name}'
    return BloomFilter(server=server, key=key, **kwargs)
