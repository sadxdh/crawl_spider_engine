"""FOMC 议息会议发布会实时字幕采集器（中英双语）

数据源：美联储官网 Brightcove 直播（live-broadcast.htm）的 CART 实时字幕（WebVTT）。
  - 会议当天，页面 data-video-id 指向直播视频；playback API 返回 text_tracks（英文字幕 VTT）。
  - 轮询 VTT（fastly 签名 URL，短期有效），增量解析新字幕段。
  - DeepSeek 批量翻译成中文，写入 crawl_data.fomc_captions（中英双语同表）。

运行（独立进程，非 Scrapy）：
  python -m collectors.fomc_captions_collector

会议日程（美东）：
  2026-09-15/16  FOMC Meeting（9/16 14:00 ET = 北京 9/17 02:00 发布会）
  2026-10-27/28  2026-12-08/09
"""
import json
import os
import re
import time
import hashlib
import urllib.request
from datetime import datetime, timedelta, timezone

import requests
from loguru import logger

from collectors.base_collector import BaseCollector

# ── Brightcove（美联储官网直播） ────────────────────────────
BC_ACCOUNT = '66043936001'
BC_PLAYER = 'default_default'
BC_POLICY_KEY = os.getenv('BC_POLICY_KEY', '')
LIVE_PAGE_URL = 'https://www.federalreserve.gov/live-broadcast.htm'
PLAYBACK_API = f'https://edge.api.brightcove.com/playback/v1/accounts/{BC_ACCOUNT}/videos/'

# ── DeepSeek 翻译 ─────────────────────────────────────────
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
DEEPSEEK_URL = 'https://api.deepseek.com/chat/completions'
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')

# ── 会议日程（美东日期 → 北京日期；发布会通常为会议第二日 14:00 ET） ──
# 格式: (美东会议日, 北京发布会日, 美东发布会时间 HH:MM)
FOMC_MEETINGS = [
    ('2026-09-16', '2026-09-17', '14:00'),  # 9/15-16 会议，16日发布会
    ('2026-10-28', '2026-10-29', '14:00'),  # 10/27-28 会议
    ('2026-12-09', '2026-12-10', '14:00'),  # 12/8-9 会议
]

POLL_INTERVAL = int(os.getenv('FOMC_POLL_INTERVAL', '20'))   # VTT 轮询间隔（秒）
WINDOW_HOURS_BEFORE = int(os.getenv('FOMC_WINDOW_HOURS', '3'))   # 会议窗口：发布会前 N 小时开始
WINDOW_HOURS_AFTER = int(os.getenv('FOMC_WINDOW_AFTER', '4'))    # 发布会后 N 小时结束采集
TRANSLATE_BATCH = int(os.getenv('FOMC_TRANSLATE_BATCH', '8'))    # 每批翻译段数

_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0'}
# Brightcove/DeepSeek 均为腾讯云可直连域名，显式禁用容器 HTTP(S)_PROXY（走代理反而被重置）
_NO_PROXY = {'http': None, 'https': None}


class FomcCaptionsCollector(BaseCollector):
    """FOMC 发布会实时字幕（Brightcove VTT → 中英双语落库）"""

    name = 'fomc_captions'
    data_table = 'fomc_captions'
    poll_interval = POLL_INTERVAL

    table_ddl = """
    CREATE TABLE IF NOT EXISTS `fomc_captions` (
      `id` BIGINT NOT NULL AUTO_INCREMENT,
      `meeting_date` VARCHAR(20) NOT NULL COMMENT '会议日（美东 YYYY-MM-DD）',
      `seq` INT NOT NULL COMMENT '字幕段序号（VTT 顺序）',
      `ts_start` FLOAT NOT NULL COMMENT '起始秒',
      `ts_end` FLOAT NOT NULL COMMENT '结束秒',
      `en_text` TEXT NOT NULL COMMENT '英文字幕',
      `zh_text` TEXT DEFAULT NULL COMMENT '中文翻译',
      `source_video` VARCHAR(40) DEFAULT '' COMMENT 'Brightcove video id',
      `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_meeting_seq` (`meeting_date`, `seq`),
      KEY `ix_meeting_ts` (`meeting_date`, `ts_start`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='FOMC 发布会实时字幕（中英双语）'
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_video_id = None
        self._vtt_url = None
        self._last_seq = 0           # 已入库最大 seq（进程内增量）
        self._active_meeting = None  # 当前会议日（美东）
        self._inactive_loops = 0     # 非会议窗口连续轮询计数（用于降频）

    # ── 会议窗口判断 ────────────────────────────────────────

    def _bj_now(self) -> datetime:
        return datetime.utcnow() + timedelta(hours=8)

    def _active_window(self) -> str | None:
        """当前是否处于 FOMC 发布会采集窗口；返回会议日（美东）或 None"""
        bj = self._bj_now()
        for meeting_et, bj_press_date, press_time_et in FOMC_MEETINGS:
            # 美东时间 = UTC-4（夏令时）；发布会时间转北京
            h, m = map(int, press_time_et.split(':'))
            press_dt_et = datetime.strptime(meeting_et, '%Y-%m-%d').replace(hour=h, minute=m)
            press_dt_utc = press_dt_et + timedelta(hours=4)
            press_dt_bj = press_dt_utc + timedelta(hours=8)
            start = press_dt_bj - timedelta(hours=WINDOW_HOURS_BEFORE)
            end = press_dt_bj + timedelta(hours=WINDOW_HOURS_AFTER)
            if start <= bj <= end:
                return meeting_et
        return None

    # ── Brightcove 数据获取 ─────────────────────────────────

    def _get_live_video_id(self) -> str | None:
        """从官网直播页提取当前 data-video-id"""
        try:
            r = requests.get(LIVE_PAGE_URL, headers=_HEADERS, timeout=15, proxies=_NO_PROXY)
            if r.status_code != 200:
                return None
            m = re.search(r'data-video-id="(\d+)"', r.text)
            return m.group(1) if m else None
        except Exception as e:
            logger.warning(f'[fomc] 直播页获取失败: {e}')
            return None

    def _get_playback(self, video_id: str) -> dict | None:
        """调 Brightcove playback API 获取视频信息（含 text_tracks）"""
        try:
            headers = dict(_HEADERS)
            if BC_POLICY_KEY:
                headers['Accept'] = f'application/json;pk={BC_POLICY_KEY}'
            else:
                headers['Accept'] = 'application/json'
            r = requests.get(PLAYBACK_API + video_id, headers=headers, timeout=20, proxies=_NO_PROXY)
            if r.status_code != 200:
                logger.warning(f'[fomc] playback API {r.status_code}: {r.text[:120]}')
                return None
            return r.json()
        except Exception as e:
            logger.warning(f'[fomc] playback 请求失败: {e}')
            return None

    @staticmethod
    def _extract_vtt_url(playback: dict) -> str | None:
        """从 playback 响应提取英文 captions VTT URL（优先 https）"""
        tracks = playback.get('text_tracks') or []
        for t in tracks:
            if t.get('kind') == 'captions' and (t.get('srclang') or '').lower().startswith('en'):
                srcs = t.get('sources') or []
                for s in srcs:
                    src = s.get('src', '')
                    if src.startswith('https://') and '.vtt' in src:
                        return src
                for s in srcs:
                    src = s.get('src', '')
                    if '.vtt' in src:
                        return src
        return None

    # ── VTT 解析 ───────────────────────────────────────────

    @staticmethod
    def _parse_vtt(vtt_text: str) -> list[dict]:
        """解析 VTT → [{seq, ts_start, ts_end, text}]（过滤空白/重复行）"""
        cues = []
        # 按 cue 块切分：时间行 + 文本
        lines = vtt_text.replace('\r\n', '\n').split('\n')
        i = 0
        seq = 0
        while i < len(lines):
            line = lines[i].strip()
            m = re.match(
                r'(\d{1,2}:\d{2}\.\d{3}|\d{1,2}:\d{2}:\d{2}\.\d{3})'
                r'\s*-->\s*'
                r'(\d{1,2}:\d{2}\.\d{3}|\d{1,2}:\d{2}:\d{2}\.\d{3})',
                line,
            )
            if m:
                start = FomcCaptionsCollector._ts_to_sec(m.group(1))
                end = FomcCaptionsCollector._ts_to_sec(m.group(2))
                text_lines = []
                j = i + 1
                while j < len(lines) and lines[j].strip() and not re.match(
                        r'\d{1,2}:\d{2}(:\d{2})?\.\d{3}\s*-->', lines[j].strip()):
                    text_lines.append(lines[j].strip())
                    j += 1
                text = ' '.join(text_lines).strip()
                if text:
                    cues.append({'seq': seq, 'ts_start': round(start, 3),
                                 'ts_end': round(end, 3), 'text': text})
                    seq += 1
                i = j
            else:
                i += 1
        return cues

    @staticmethod
    def _ts_to_sec(ts: str) -> float:
        parts = ts.split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])

    # ── DeepSeek 翻译 ───────────────────────────────────────

    def _translate_batch(self, items: list[dict]) -> list[dict]:
        """批量翻译 items（含 seq + en_text），返回带 zh_text 的 items"""
        if not DEEPSEEK_API_KEY:
            logger.warning('[fomc] 未配置 DEEPSEEK_API_KEY，跳过翻译')
            return items
        texts = [it['text'] for it in items]
        prompt = (
            '你是专业的金融翻译。将以下英文（美联储 FOMC 发布会逐字稿片段）逐条翻译为简体中文，'
            '保持金融术语准确，口语化自然。只输出翻译结果，每条一行，用编号前缀 "1." "2." ... 对应输入。\n\n'
            + '\n'.join(f'{i+1}. {t}' for i, t in enumerate(texts))
        )
        body = json.dumps({
            'model': DEEPSEEK_MODEL,
            'messages': [
                {'role': 'system', 'content': 'You are a professional financial translator (EN->ZH).'},
                {'role': 'user', 'content': prompt},
            ],
            'max_tokens': 4096,
            'temperature': 0.2,
        }).encode('utf-8')
        req = urllib.request.Request(
            DEEPSEEK_URL, data=body,
            headers={'Content-Type': 'application/json',
                     'Authorization': f'Bearer {DEEPSEEK_API_KEY}'},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            content = data['choices'][0]['message']['content']
            # 解析编号行
            results = {}
            for m in re.finditer(r'^(\d+)\.\s*(.+)$', content, re.M):
                idx = int(m.group(1)) - 1
                results[idx] = m.group(2).strip()
            for i, it in enumerate(items):
                if i in results:
                    it['zh'] = results[i]
                else:
                    it['zh'] = ''
            return items
        except Exception as e:
            logger.warning(f'[fomc] 翻译失败: {e}')
            for it in items:
                it['zh'] = ''
            return items

    # ── 主轮询 ─────────────────────────────────────────────

    def poll_once(self) -> list:
        meeting = self._active_window()
        if not meeting:
            self._inactive_loops += 1
            if self._inactive_loops % 12 == 1:
                logger.info('[fomc] 非会议窗口，休眠等待')
            return []
        self._inactive_loops = 0

        # 1. 解析直播页拿最新 video id
        video_id = self._get_live_video_id()
        if not video_id:
            return []
        if video_id != self._current_video_id:
            logger.info(f'[fomc] 检测到发布会视频: {video_id}')
            self._current_video_id = video_id
            self._vtt_url = None
            self._last_seq = 0
            playback = self._get_playback(video_id)
            if playback:
                self._vtt_url = self._extract_vtt_url(playback)
                if self._vtt_url:
                    logger.info(f'[fomc] 字幕 VTT 就绪 (video={video_id})')
                else:
                    logger.warning('[fomc] playback 未找到英文字幕轨道')
                    return []
        if not self._vtt_url:
            # 首次或尚未拿到 VTT，重试一次
            playback = self._get_playback(video_id)
            if playback:
                self._vtt_url = self._extract_vtt_url(playback)
            if not self._vtt_url:
                return []

        # 2. 拉取 VTT 增量
        try:
            r = requests.get(self._vtt_url, headers=_HEADERS, timeout=20, proxies=_NO_PROXY)
            if r.status_code != 200:
                logger.warning(f'[fomc] VTT 获取 {r.status_code}')
                return []
            cues = self._parse_vtt(r.text)
        except Exception as e:
            logger.warning(f'[fomc] VTT 请求失败: {e}')
            return []

        new_cues = [c for c in cues if c['seq'] > self._last_seq]
        if not new_cues:
            return []
        self._last_seq = max(c['seq'] for c in cues)

        # 3. 翻译（分批）
        rows = []
        for i in range(0, len(new_cues), TRANSLATE_BATCH):
            batch = new_cues[i:i + TRANSLATE_BATCH]
            batch = self._translate_batch(batch)
            for c in batch:
                rows.append({
                    'meeting_date': meeting,
                    'seq': c['seq'],
                    'ts_start': c['ts_start'],
                    'ts_end': c['ts_end'],
                    'en_text': c['text'],
                    'zh_text': c.get('zh') or None,
                    'source_video': self._current_video_id,
                })
        if rows:
            logger.info(f'[fomc] 新增字幕 {len(rows)} 段 (seq {rows[0]["seq"]}..{rows[-1]["seq"]}, {meeting})')
        return rows


if __name__ == '__main__':
    FomcCaptionsCollector().start()
