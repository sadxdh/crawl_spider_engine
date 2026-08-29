"""流式采集器基类

复用 crawl 平台现有 Redis 心跳/统计协议（与管理平台兼容），提供：
  - 心跳上报（每 30s，TTL 120s）
  - 统计累计与上报（每 60s 写 yuncrawl_stats:{name}）
  - 批量落库 crawl_data（攒批 + INSERT IGNORE，全量落库原则 v6.2）

用法：子类实现 `poll_once() -> list[dict]`（返回待入库行），循环由基类驱动。
"""
import os
import threading
import time
from loguru import logger

# 采集器出网策略：
#   - 默认直连（NO_PROXY），禁用 TradingSystem 业务侧 HTTP_PROXY（那会导致采集失败）
#   - 若配置了 CRAWL_OUTBOUND_PROXY（如本地 SSRDOG host:9567），作为兜底代理
#     （get_proxies() 返回：有代理则走代理，无则直连）
_OUTBOUND_PROXY = os.getenv('CRAWL_OUTBOUND_PROXY', '').strip()
NO_PROXY = {'http': None, 'https': None}


def get_proxies():
    """返回 requests 用的 proxies 参数：配置了 CRAWL_OUTBOUND_PROXY 则走代理，否则直连"""
    if _OUTBOUND_PROXY:
        return {'http': _OUTBOUND_PROXY, 'https': _OUTBOUND_PROXY}
    return NO_PROXY


class BaseCollector:
    """流式采集器基类

    子类需定义：
      name          — 采集器名（用于心跳/统计 key，如 flash_news）
      data_table    — crawl_data 目标表
      poll_interval — 轮询间隔（秒）
      poll_once()   — 单次采集，返回 list[dict]（dict 为待入库行，含唯一键字段）
    """

    name = 'base'
    data_table = ''
    poll_interval = 60
    batch_size = 200          # 落库攒批阈值
    heartbeat_interval = 30   # 心跳间隔（秒）
    stats_interval = 60       # 统计上报间隔（秒）

    def __init__(self, redis_client=None, mysql_get_conn=None):
        self._redis = redis_client
        self._mysql_get_conn = mysql_get_conn
        self._stop = threading.Event()
        self._stats = {'scraped': 0, 'inserted': 0, 'dropped': 0, 'errors': 0}
        self._stats_lock = threading.Lock()
        self._last_heartbeat = 0.0
        self._last_stats = 0.0

    # ── 对外入口 ─────────────────────────────────────────────

    def start(self):
        """启动采集循环（阻塞）；子类在独立线程/进程调用"""
        self._redis = self._redis or self._get_redis()
        self._mysql_get_conn = self._mysql_get_conn or self._get_mysql()
        logger.info(f'[Collector:{self.name}] 启动 poll_interval={self.poll_interval}s '
                    f'table={self.data_table}')
        # 订阅 admin 控制指令（§3.3：crawl_admin_server Redis pub/sub 统一调度）
        self._start_cmd_listener()
        while not self._stop.is_set():
            t0 = time.monotonic()
            try:
                rows = self.poll_once() or []
                self._persist(rows)
                self._bump('scraped', len(rows))
            except Exception as e:
                self._bump('errors', 1)
                logger.warning(f'[Collector:{self.name}] 轮询异常: {e}')
            self._heartbeat_if_due()
            self._stats_if_due()
            elapsed = time.monotonic() - t0
            self._stop.wait(max(1.0, self.poll_interval - elapsed))

    def stop(self):
        self._stop.set()

    # ── admin 控制指令监听（§3.3 统一调度） ─────────────────────

    def _start_cmd_listener(self):
        """订阅 Redis crawl_admin:collector:cmd，处理 start/stop/restart 广播

        幂等健壮：Redis 不可达时 subscribe 会阻塞较久，这里用独立线程 + 短超时，
        失败仅记 warning 不阻塞主轮询循环（v6.3 §10.62 部署健壮性）。
        """
        try:
            if not self._redis:
                return
            import json as _json
            import threading as _t
            cmd_key = 'crawl_admin:collector:cmd'

            def _listen():
                try:
                    self._redis.connection_pool.connection_kwargs.setdefault(
                        'socket_connect_timeout', 3)
                    self._redis.connection_pool.connection_kwargs.setdefault(
                        'socket_timeout', 5)
                except Exception:
                    pass
                try:
                    ps = self._redis.pubsub()
                    ps.subscribe(cmd_key)
                    logger.info(f'[Collector:{self.name}] 控制指令监听已启动 ({cmd_key})')
                    for msg in ps.listen():
                        if self._stop.is_set():
                            break
                        if msg.get('type') != 'message':
                            continue
                        try:
                            data = _json.loads(msg['data'])
                        except Exception:
                            continue
                        if data.get('collector') not in (self.name, '*'):
                            continue
                        action = data.get('action')
                        logger.info(f'[Collector:{self.name}] 收到指令: {action}')
                        if action == 'stop':
                            self.stop()
                            break
                        elif action == 'restart':
                            logger.info(f'[Collector:{self.name}] 重启指令（本进程按 stop 处理，由进程管理器拉起）')
                            self.stop()
                            break
                        # start 指令：已在运行则忽略
                except Exception as e:
                    logger.warning(f'[Collector:{self.name}] 控制指令监听不可用（不影响采集）: {e}')
            t = _t.Thread(target=_listen, daemon=True, name=f'{self.name}-cmd')
            t.start()
        except Exception as e:
            logger.warning(f'[Collector:{self.name}] 指令监听启动失败（不影响采集）: {e}')

    # ── 子类实现 ─────────────────────────────────────────────

    def poll_once(self) -> list:
        raise NotImplementedError

    # ── 基础设施注入点（可被子类/测试覆盖） ──────────────────

    def _get_redis(self):
        from utils.redis_client import get_redis
        return get_redis()

    def _get_mysql(self):
        from utils.mysql_pool import get_mysql
        return get_mysql  # 返回工厂函数（_persist 每次调用取新连接），不是连接本身

    # ── 心跳 / 统计 ──────────────────────────────────────────

    def _heartbeat_if_due(self):
        now = time.time()
        if now - self._last_heartbeat < self.heartbeat_interval:
            return
        self._last_heartbeat = now
        try:
            if self._redis:
                self._redis.setex(f'crawl_engine:heartbeat:{self.name}', 120, '1')
        except Exception as e:
            logger.debug(f'[Collector:{self.name}] 心跳失败: {e}')

    def _stats_if_due(self):
        now = time.time()
        if now - self._last_stats < self.stats_interval:
            return
        self._last_stats = now
        with self._stats_lock:
            stats = dict(self._stats)
            self._stats = {'scraped': 0, 'inserted': 0, 'dropped': 0, 'errors': 0}
        try:
            if self._redis:
                self._redis.hset(f'yuncrawl_stats:{self.name}', mapping={
                    'item_scraped_count': stats['scraped'],
                    'item_dropped_count': stats['dropped'],
                    'errors': stats['errors'],
                    'timestamp': int(time.time()),
                })
        except Exception as e:
            logger.debug(f'[Collector:{self.name}] 统计上报失败: {e}')

    def _bump(self, key: str, n: int):
        with self._stats_lock:
            self._stats[key] = self._stats.get(key, 0) + n

    # ── 落库（全量落 crawl_data，v6.2） ───────────────────────

    def _persist(self, rows: list):
        """落库到 self.data_table（默认）"""
        if not rows:
            return
        self._persist_to(self.data_table, rows)

    def _persist_to(self, table: str, rows: list):
        """落库到指定表（数据源细分：每源/每频道一表，自动建表）

        v6.3 §10.46：爬虫库按数据源细分——news_sina/news_wallst/...、tg_<channel> 各一张表。
        子类通过 self._table_ddl_for(table) 提供按表 DDL，缺省用 self.table_ddl。
        """
        if not rows or not self._mysql_get_conn:
            return
        conn = self._mysql_get_conn()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute('SHOW TABLES LIKE %s', (table,))
            if not cur.fetchone():
                ddl = self._table_ddl_for(table)
                if ddl:
                    cur.execute(ddl)
                    logger.info(f'[Collector:{self.name}] 已创建表 {table}')
            cols = list(rows[0].keys())
            col_sql = ', '.join(f'`{c}`' for c in cols)
            placeholders = ', '.join(['%s'] * len(cols))
            sql = f'INSERT IGNORE INTO `{table}` ({col_sql}) VALUES ({placeholders})'
            batch = []
            for row in rows:
                batch.append(tuple(row.get(c) for c in cols))
                if len(batch) >= self.batch_size:
                    cur.executemany(sql, batch)
                    batch = []
            if batch:
                cur.executemany(sql, batch)
            conn.commit()
            self._bump('inserted', len(rows))
        except Exception as e:
            logger.warning(f'[Collector:{self.name}] 落库 {table} 失败: {e}')
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            try:
                if cur is not None:
                    cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    def _table_ddl_for(self, table: str) -> str:
        """按表生成 DDL（细分表用；缺省返回类级 table_ddl）"""
        ddl = getattr(self, 'table_ddl', None)
        if ddl and '`{table}`' in ddl:
            return ddl.format(table=table)
        return ddl

    def _ensure_table(self, cur):
        """目标表不存在时按子类 table_ddl 建表（全量落库前自愈）"""
        ddl = getattr(self, 'table_ddl', None)
        if ddl:
            cur.execute(ddl)
            logger.info(f'[Collector:{self.name}] 已创建表 {self.data_table}')
