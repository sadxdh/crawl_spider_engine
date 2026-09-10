"""TG 频道快讯流采集器（T1 收编 C2 · 情报部 news_tg.py 迁入）

Telethon MTProto 事件驱动，与轮询型 BaseCollector 不同：独立 asyncio 事件循环，
NewMessage 回调 → 构造行 → 攒批落 crawl_data.tg_<channel>（每频道一表，v6.3 §10.46 细分）。
心跳/统计复用 Redis 协议（crawl_engine:heartbeat:tg_news / yuncrawl_stats:tg_news）。

依赖：telethon + pyaes + PySocks/python-socks（缺失时降级为未配置并告警）。
频道配置（v6.3 §10.57 配置化热添加）：
  1. DB 配置表 crawl_data.tg_channel_config（管理端 /collectors/channels API 维护，
     enabled=1 的频道被自动监听）；采集器每 CONFIG_REFRESH 秒刷新一次，
     新增频道无需重启进程 → 配置即热添加。
  2. 环境变量 TG_NEWS_CHANNELS(逗号分隔) 作为兜底（与 DB 配置合并）。
其他环境变量（对齐情报部）：
  TG_API_ID / TG_API_HASH / TG_SESSION_STRING
  PROXY_HOST / PROXY_PORT（socks5，可选；不设则直连）

运行（独立进程，非 Scrapy）：
  python -m collectors.tg_collector
"""
import asyncio
import os
import threading
import time
from datetime import datetime, timezone, timedelta

from loguru import logger

from collectors.base_collector import BaseCollector
from collectors.flash_news_collector import _md5, _strip_html

TZ_CST = timezone(timedelta(hours=8))
HEARTBEAT_INTERVAL = 30
CONFIG_REFRESH = 60  # 频道配置刷新周期（秒）：热添加生效窗口


def _fmt_dt(dt) -> str:
    if not dt:
        return datetime.now(TZ_CST).strftime('%Y-%m-%d %H:%M:%S')
    if dt.tzinfo is None:
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    return dt.astimezone(TZ_CST).strftime('%Y-%m-%d %H:%M:%S')


class TgNewsCollector(BaseCollector):
    """TG 频道快讯采集器：Telethon 事件驱动 → 每频道一表 crawl_data.tg_<channel>"""

    name = 'tg_news'
    data_table = 'tg_news'  # 占位；实际落 tg_<channel> 每频道表
    poll_interval = 1  # 事件驱动，无轮询；心跳节拍由 _heartbeat_loop 控制

    # 通用 TG 快讯表 DDL（`{table}` 占位 → 每频道建表）
    table_ddl = """
    CREATE TABLE IF NOT EXISTS `{table}` (
      `id` BIGINT NOT NULL AUTO_INCREMENT,
      `news_id` VARCHAR(80) NOT NULL COMMENT '频道消息ID（tg_<channel>_<msgid>）',
      `text` TEXT NOT NULL COMMENT '消息文本',
      `source` VARCHAR(50) NOT NULL COMMENT '频道用户名',
      `tag` VARCHAR(50) DEFAULT 'crypto' COMMENT '标签',
      `docurl` VARCHAR(500) DEFAULT '' COMMENT '原文链接',
      `news_time` DATETIME NOT NULL COMMENT '消息时间',
      `collected_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      `md5_value` VARCHAR(64) NOT NULL COMMENT '去重键（text|channel|msgid）',
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_md5` (`md5_value`),
      KEY `ix_source` (`source`),
      KEY `ix_news_time` (`news_time`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='TG 频道快讯（T1 收编 C2 · 每频道一表）'
    """

    def __init__(self, api_id='', api_hash='', channels='', session_string='',
                 proxy_host='', proxy_port=0, **kwargs):
        super().__init__(**kwargs)
        self.api_id = api_id or os.getenv('TG_API_ID', '')
        self.api_hash = api_hash or os.getenv('TG_API_HASH', '')
        self.channels_str = channels or os.getenv('TG_NEWS_CHANNELS', '')
        self.session_string = session_string or os.getenv('TG_SESSION_STRING', '')
        # 代理可选：设了 PROXY_HOST 才走代理（本地直连；线上走 Clash/SSRDOG）
        self.proxy_host = proxy_host or os.getenv('PROXY_HOST', '')
        self.proxy_port = int(proxy_port or os.getenv('PROXY_PORT', '0') or 0)
        self._buffer = []
        self._buffer_lock = threading.Lock()
        self._last_flush = 0.0
        # 动态频道集合（v6.3 §10.57 热添加）：DB 配置 + 环境变量合并，定期刷新
        self._channels: list[str] = []
        self._channels_lock = threading.Lock()

    # ── 频道配置（DB tg_channel_config 优先 + 环境变量兜底） ─────

    def _load_channels(self) -> list:
        """从 DB tg_channel_config(enabled=1) + TG_NEWS_CHANNELS 合并频道列表"""
        channels: list[str] = []
        try:
            if not self._mysql_get_conn:
                self._mysql_get_conn = self._get_mysql()
            conn = self._mysql_get_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "CREATE TABLE IF NOT EXISTS `tg_channel_config` ("
                        " `id` INT NOT NULL AUTO_INCREMENT,"
                        " `channel` VARCHAR(100) NOT NULL COMMENT 'TG频道用户名（不含@）',"
                        " `display_name` VARCHAR(200) DEFAULT '' COMMENT '频道显示名/备注',"
                        " `enabled` TINYINT NOT NULL DEFAULT 1 COMMENT '是否启用 1=是 0=否',"
                        " `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                        " `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,"
                        " PRIMARY KEY (`id`), UNIQUE KEY `uk_channel` (`channel`)"
                        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='TG频道采集配置（配置即热添加）'")
                    cur.execute("SELECT channel FROM tg_channel_config WHERE enabled=1 ORDER BY id")
                    for r in cur.fetchall():
                        ch = (r['channel'] or '').strip().lstrip('@')
                        if ch and ch not in channels:
                            channels.append(ch)
            except Exception as e:
                logger.warning(f'[tg_news] 读取频道配置失败: {e}')
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f'[tg_news] 频道配置连接失败: {e}')
        # 环境变量兜底
        for ch in self.channels_str.split(','):
            ch = ch.strip().lstrip('@')
            if ch and ch not in channels:
                channels.append(ch)
        return channels

    def _refresh_channels(self, client=None):
        """刷新频道集合（热添加）：DB 变更后下一周期自动补监听"""
        new_list = self._load_channels()
        with self._channels_lock:
            old_set = set(self._channels)
            added = [c for c in new_list if c not in old_set]
            removed = [c for c in self._channels if c not in new_list]
            self._channels = new_list
        if added or removed:
            logger.info(f'[tg_news] 频道配置变更: +{len(added)} -{len(removed)} → {len(new_list)} 个')
            for c in added:
                logger.info(f'[tg_news] 热添加频道: {c}')
        return added

    # ── 主入口（事件驱动，覆写 BaseCollector.start） ─────────────

    def start(self):
        try:
            api_id_int = int(self.api_id)
        except (ValueError, TypeError):
            api_id_int = 0
        if api_id_int <= 0 or not self.api_hash or not self.session_string:
            logger.warning('[tg_news] 未配置 TG_API_ID/TG_API_HASH/TG_SESSION_STRING，跳过监听')
            return
        # 首次加载频道（DB 配置 + 环境变量）
        self._refresh_channels()

        try:
            from telethon import TelegramClient, events  # noqa: F401
            from telethon.sessions import StringSession  # noqa: F401
        except ImportError as e:
            logger.error(f'[tg_news] Telethon 未安装，TG 监听不可用: {e}')
            return

        self._redis = self._redis or self._get_redis()
        self._mysql_get_conn = self._mysql_get_conn or self._get_mysql()

        with self._channels_lock:
            channel_count = len(self._channels)
        logger.info(f'[tg_news] 启动 MTProto: {channel_count} 频道'
                    f'{" socks5://" + self.proxy_host + ":" + str(self.proxy_port) if self.proxy_host else "（直连）"}')

        # 心跳线程（事件循环里没有轮询节拍）
        t = threading.Thread(target=self._heartbeat_loop, daemon=True, name='tg-heartbeat')
        t.start()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._listen())
        except KeyboardInterrupt:
            logger.info('[tg_news] 收到退出信号')
        except Exception as e:
            logger.error(f'[tg_news] 异常退出: {e}')
        finally:
            self._flush(force=True)
            try:
                loop.close()
            except Exception:
                pass

    def _heartbeat_loop(self):
        while not self._stop.is_set():
            self._heartbeat_if_due()
            # 每 5s 也顺带 flush 缓冲
            self._flush()
            self._stop.wait(5)

    # ── 异步监听 ───────────────────────────────────────────────

    async def _listen(self):
        from telethon import TelegramClient, events
        from telethon.sessions import StringSession

        kwargs = {}
        if self.proxy_host and self.proxy_port:
            try:
                from python_socks import ProxyType  # noqa: F401  # 代理支持库
                kwargs['proxy'] = ('socks5', self.proxy_host, self.proxy_port)
            except ImportError:
                logger.warning('[tg_news] python-socks 未安装，忽略代理直连')
        client = TelegramClient(
            StringSession(self.session_string),
            int(self.api_id), self.api_hash,
            **kwargs,
        )
        try:
            await client.connect()
        except Exception as e:
            logger.error(f'[tg_news] 连接失败(代理/网络): {e}')
            return
        if not await client.is_user_authorized():
            logger.error('[tg_news] TG Session 无效或已过期，请重新生成 TG_SESSION_STRING')
            await client.disconnect()
            return

        # 活跃频道实体集合（热添加：事件回调按 chat_id 过滤）
        self._active_entities = set()
        with self._channels_lock:
            channels = list(self._channels)
        resolved = []
        for ch in channels:
            try:
                ent = await client.get_entity(ch)
                resolved.append(ent)
                self._active_entities.add(_peer_id(ent))
                logger.info(f'[tg_news] 频道已解析: {ch}')
            except Exception as e:
                logger.warning(f'[tg_news] 频道解析失败: {ch} — {e}')
        if not resolved:
            logger.warning('[tg_news] 无有效频道')
            await client.disconnect()
            return

        @client.on(events.NewMessage())
        async def handler(event):
            # 热添加过滤：仅处理活跃频道集合中的消息
            try:
                chat_id = event.chat_id
                if chat_id not in self._active_entities:
                    return
                text = _strip_html(event.message.text or '')
                if not text or len(text) < 10:
                    return
                chat = await event.get_chat()
                ch_name = getattr(chat, 'username', '') or str(event.chat_id)
                ntime = _fmt_dt(event.message.date) if event.message.date else \
                    datetime.now(TZ_CST).strftime('%Y-%m-%d %H:%M:%S')
                row = {
                    'news_id': f'tg_{ch_name}_{event.message.id}',
                    'text': text[:3000],
                    'source': ch_name,
                    'tag': 'crypto',
                    'docurl': '',
                    'news_time': ntime,
                    'md5_value': _md5(f'{text}|{ch_name}|{event.message.id}'),
                }
                with self._buffer_lock:
                    self._buffer.append(row)
                self._bump('scraped', 1)
                self._flush()
            except Exception:
                pass

        logger.info(f'[tg_news] 开始监听 {len(resolved)} 个频道')
        # 热添加周期任务：DB 频道配置变更 → 自动解析新实体入监听集合（配置即热添加）
        async def hot_add_loop():
            while not self._stop.is_set():
                try:
                    added = self._refresh_channels()
                    if added:
                        for ch in added:
                            try:
                                ent = await client.get_entity(ch)
                                self._active_entities.add(_peer_id(ent))
                                logger.info(f'[tg_news] 热添加生效: {ch} (id={ent.id})')
                            except Exception as e:
                                logger.warning(f'[tg_news] 热添加频道解析失败: {ch} — {e}')
                except Exception as e:
                    logger.debug(f'[tg_news] 热添加刷新异常: {e}')
                await asyncio.sleep(CONFIG_REFRESH)

        await asyncio.gather(client.run_until_disconnected(), hot_add_loop())

    # ── 攒批落库（按频道分表） ─────────────────────────────────

    def _flush(self, force: bool = False):
        now = time.time()
        with self._buffer_lock:
            if not self._buffer:
                return
            if not force and now - self._last_flush < 5 and len(self._buffer) < self.batch_size:
                return
            rows, self._buffer = self._buffer, []
            self._last_flush = now
        try:
            # 按频道分组 → tg_<channel> 各表（v6.3 §10.46 细分）
            by_channel: dict[str, list] = {}
            for r in rows:
                ch = r.get('source', 'unknown')
                by_channel.setdefault(ch, []).append(r)
            for ch, ch_rows in by_channel.items():
                table = f"tg_{_safe_table(ch)}"
                self._persist_to(table, ch_rows)
        except Exception as e:
            logger.warning(f'[tg_news] 落库失败: {e}')

    def _table_ddl_for(self, table: str) -> str:
        return self.table_ddl.format(table=table)


def _peer_id(entity):
    """Telethon entity -> marked chat_id (channels carry the -100 prefix).

    event.chat_id is the *marked* peer id (e.g. -1001234567890) whereas
    entity.id is the raw id; comparing them directly never matches, so every
    message was dropped silently and no TG rows were ever persisted.
    """
    try:
        from telethon import utils as _tu
        return _tu.get_peer_id(entity)
    except Exception:
        return getattr(entity, "id", None)


def _safe_table(name: str) -> str:
    """频道名 → 安全表名（小写、仅字母数字下划线）"""
    return ''.join(c if c.isalnum() or c == '_' else '_' for c in name.lower())[:50]


def main():
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    collector = TgNewsCollector()
    collector.start()


if __name__ == '__main__':
    main()
