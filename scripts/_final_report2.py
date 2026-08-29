"""生成准确的爬虫字段逻辑对比报告 - 处理_table路由和变量yield"""
import os, re, ast, json, pymysql
from datetime import datetime
from collections import defaultdict

SPIDER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'spiders')
OLD_DIR = r'C:\Users\24613\workstation\data_crawl_server\spider'
REPORT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs', 'spider_field_audit.md')

AUTO_COLS = {'id', 'created_time', 'updated_time', 'update_time', 'create_time', 'crawl_time'}
SKIP_FILES = {'amac_manager.py', 'gov_bidding_spider.py', 'qyyjt_bond_issue_spider.py', 'hk_listing_spider.py'}

# 获取 DB 表列
conn = pymysql.connect(host='py.w.com', user='root', password='IK29lKb0', database='crawl_data', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
table_cols = {}
with conn.cursor() as cur:
    cur.execute('SHOW TABLES')
    for r in cur.fetchall():
        t = list(r.values())[0]
        with conn.cursor() as c2:
            c2.execute(f"SHOW COLUMNS FROM `{t}`")
            table_cols[t] = {r2['Field']: r2['Type'] for r2 in c2.fetchall() if r2['Field'] not in AUTO_COLS}
conn.close()

# 新旧爬虫名称映射 (新spider_name → 旧项目关键词)
OLD_MAP = {
    'report_tax_anhui': 'anhui_tax_spider',
    'report_tax_beijing': 'beijing_tax_spider',
    'report_tax_chongqing': 'chongqing_tax_spider',
    'report_tax_dalian': 'dalian_tax_spider',
    'report_tax_fujian': 'fujian_tax_spider',
    'report_tax_gansu': 'gansu_tax_spider',
    'report_tax_guangdong': 'guangdong_tax_spider',
    'report_tax_guangxi': 'guangxi_tax_spider',
    'report_tax_guizhou': 'guizhou_tax_spider',
    'report_tax_hainan': 'hainan_tax_spider',
    'report_tax_hebei': 'hebei_tax_spider',
    'report_tax_henan': 'henan_tax_spider',
    'report_tax_hlj': 'hlj_tax_spider',
    'report_tax_hubei': 'hubei_tax_spider',
    'report_tax_hunan': 'hunan_tax_spider',
    'report_tax_jiangsu': 'jiangsu_tax_spider',
    'report_tax_jiangxi': 'jiangxi_tax_spider',
    'report_tax_jilin': 'jilin_tax_spider',
    'report_tax_liaoning': 'liaoning_tax_spider',
    'report_tax_ningxia': 'ningxia_tax_spider',
    'report_tax_nmg': 'nmg_tax_spider',
    'report_tax_qinghai': 'qinghai_tax_spider',
    'report_tax_shandong': 'shandong_tax_spider',
    'report_tax_shanghai': 'sh_tax_spider',
    'report_tax_shanxi': 'shanxi_tax_spider',
    'report_tax_shenzhen': 'shenzhen_tax_spider',
    'report_tax_sichuan': 'sichuan_tax_spider',
    'report_tax_tianjin': 'tianjin_tax_spider',
    'report_tax_xiamen': 'xiamen_tax_spider',
    'report_tax_xinjiang': 'xinjiang_tax_spider',
    'report_tax_xizang': 'xizang_tax_spider',
    'report_tax_yunnan': 'yunnan_tax_spider',
    'report_tax_zhejiang': 'zhejiang_tax_spider',
    'report_tax_ningbo': 'ningbo_tax_spider',
    'report_tax_qingdao': 'qingdao_tax_spider',
    'finance_trust_finance': 'trust_finance',
    'report_finance_manage': 'shandong_finance',
    'economy_standard_info': 'standard_info',
    'finance_ipo_declare_a_shares': 'ipo_',
    'report_company_announcement': 'company_announcement',
    'report_bond_announcement': 'bond_announcement',
    'economy_person_pedia': 'askci',
    'economy_bill_default': 'bill_file',
    'economy_material_cneptp': 'cneptp_material',
    'economy_jiangsu_gdjg': 'gdjg_jiangsu',
    'economy_jiangsu_gdgg': 'gdgg_jiangsu',
    'economy_jiangsu_dkgs': 'dkgs_jiangsu',
    'economy_cjgs_land': 'cjgs_land',
    'economy_crgg_land': 'crgg_land',
    'economy_jggg_land': 'jggg_land',
    'law_case': 'rmfy_case',
    'law_firm': 'law_firm',
    'law_legal_risk': 'shgjrmfy',
}


class SpiderAnalyzer:
    def __init__(self, filepath):
        self.path = filepath
        self.rel = os.path.relpath(filepath, SPIDER_DIR)
        self.fname = os.path.basename(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            self.source = f.read()
        self.lines = self.source.split('\n')

        # Extract basic info
        m = re.search(r"data_table\s*=\s*'([^']+)'", self.source) or re.search(r'data_table\s*=\s*"([^"]+)"', self.source)
        self.data_table = m.group(1) if m else None

        m = re.search(r"name\s*=\s*'([^']+)'", self.source) or re.search(r'name\s*=\s*"([^"]+)"', self.source)
        self.spider_name = m.group(1) if m else None

        m = re.search(r"dedup_fields\s*=\s*\[(.*?)\]", self.source)
        self.dedup = m.group(1).replace("'", "").replace('"', "").strip() if m else ''

        # Find all data yields with their target tables
        self.yields = []  # [(table, fields_set)]
        self._extract_yields()

    def _extract_yields(self):
        """提取所有 yield/return dict，正确处理 _table 路由"""
        try:
            tree = ast.parse(self.source)
        except SyntaxError:
            return

        for node in ast.walk(tree):
            if not isinstance(node, (ast.Yield, ast.Return)):
                continue
            if node.value is None:
                continue

            d = None
            if isinstance(node.value, ast.Dict):
                d = node.value
            # Skip non-dict yields (like yield scrapy.Request)

            if d is None:
                continue

            routing = None
            sfields = set()
            for k, v in zip(d.keys, d.values):
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    sfields.add(k.value)
                    if k.value == '_table' and isinstance(v, ast.Constant):
                        routing = v.value

            target = routing or self.data_table
            sfields = sfields - {'_table'}
            if target and target in table_cols:
                self.yields.append((target, sfields))

    def get_all_issues(self):
        """按目标表聚合所有问题"""
        table_issues = defaultdict(lambda: {'extra': set(), 'missing': set()})
        for target, fields in self.yields:
            db_cols = set(table_cols[target].keys())
            extra = fields - db_cols
            missing = db_cols - fields
            table_issues[target]['extra'] |= extra
            table_issues[target]['missing'] |= missing
        return table_issues

    def find_old_spider(self):
        """在旧项目中查找对应的蜘蛛"""
        name = self.spider_name
        if name and name in OLD_MAP:
            keyword = OLD_MAP[name]
            for root, dirs, files in os.walk(OLD_DIR):
                for f in files:
                    if keyword in f.lower() and f.endswith('.py') and f != '__init__.py':
                        return os.path.relpath(os.path.join(root, f), OLD_DIR)
        return None

    @property
    def is_data_spider(self):
        return len(self.yields) > 0


# 收集所有蜘蛛
spiders = []
for root, dirs, files in os.walk(SPIDER_DIR):
    for f in sorted(files):
        if not f.endswith('.py') or f.startswith('__') or f == 'base_spider.py':
            continue
        path = os.path.join(root, f)
        spiders.append(SpiderAnalyzer(path))

# 按目录分组
cats = defaultdict(list)
for s in spiders:
    cats[os.path.dirname(s.rel) or 'root'].append(s)

# 生成报告
lines = []
lines.append("# 爬虫字段逻辑对比报告")
lines.append(f"\n> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
lines.append(f"> 项目: crawl_spider_engine")
lines.append(f"> 数据库: crawl_data (66表)")
lines.append(f"> 总蜘蛛数: {len(spiders)}")
lines.append(f"")

# Summary first
total_clean = 0
total_data = 0
total_issues = 0
total_skip = 0

for cat in sorted(cats.keys()):
    lines.append(f"## {cat}")
    lines.append(f"")
    lines.append(f"| 蜘蛛 | 目标表 | 字段/DB | 状态 | 旧项目 |")
    lines.append(f"|------|--------|---------|------|--------|")

    for s in cats[cat]:
        if not s.data_table:
            lines.append(f"| {s.fname} | - | - | 配置/基类 | - |")
            continue

        if s.fname in SKIP_FILES:
            lines.append(f"| {s.fname} | {s.data_table} | -/- | ⚠️ 已知问题 | - |")
            total_skip += 1
            continue

        issues = s.get_all_issues()
        if not s.is_data_spider:
            lines.append(f"| {s.fname} | {s.data_table} | -/- | 基类 | - |")
            continue

        total_data += 1
        old = s.find_old_spider()

        if issues:
            # Show per-table status
            for target, iss in issues.items():
                extra_n = len(iss['extra'])
                missing_n = len(iss['missing'])
                db_n = len(table_cols.get(target, {}))
                field_n = db_n - missing_n + extra_n if target in table_cols else '?'

                if extra_n == 1 and missing_n > 5:
                    # Likely AST false positive (cookie helper etc)
                    status = f"🟡 误报"
                    total_clean += 1
                elif extra_n == 0 and missing_n == 0:
                    status = "✅"
                    total_clean += 1
                else:
                    status = f"EXTRA={extra_n} MISS={missing_n}"
                    total_issues += 1

                lines.append(f"| {s.fname} | {target} | {field_n}/{db_n} | {status} | {old or '-'} |")
        else:
            for target, _ in [(s.data_table, set())]:
                db_n = len(table_cols.get(target, {}))
                lines.append(f"| {s.fname} | {target} | {db_n}/{db_n} | ✅ | {old or '-'} |")
            total_clean += 1

    lines.append(f"")

# Detail section for spiders with real issues
lines.append(f"## 详情: 实际不匹配项")
lines.append(f"")

for s in spiders:
    if s.fname in SKIP_FILES or not s.is_data_spider:
        continue
    issues = s.get_all_issues()
    real_issues = {t: i for t, i in issues.items() if i['extra'] or i['missing']}
    # Filter out false positives (single extra field with many missing)
    real_issues = {t: i for t, i in real_issues.items()
                   if not (len(i['extra']) <= 2 and len(i['missing']) > len(table_cols.get(t, {})) * 0.8)}

    if not real_issues:
        continue

    old = s.find_old_spider()
    lines.append(f"### {s.rel}")
    lines.append(f"- 旧项目: {old or '未找到'}")
    lines.append(f"")

    for target, iss in real_issues.items():
        db_cols = table_cols.get(target, {})
        lines.append(f"**目标表: {target}** ({len(db_cols)} 列)")
        lines.append(f"")

        if iss['extra']:
            lines.append(f"| EXTRA字段 | 说明 |")
            lines.append(f"|----------|------|")
            for col in sorted(iss['extra']):
                lines.append(f"| {col} | 蜘蛛产出, 表中无此列 |")
            lines.append(f"")

        if iss['missing']:
            lines.append(f"| MISSING字段 | DB类型 | 说明 |")
            lines.append(f"|-----------|--------|------|")
            for col in sorted(iss['missing']):
                col_type = db_cols.get(col, '?')
                lines.append(f"| {col} | {col_type} | 表中有, 蜘蛛未产出 |")
            lines.append(f"")

# Final summary
lines.append(f"## 统计")
lines.append(f"")
lines.append(f"| 类别 | 数量 |")
lines.append(f"|------|------|")
lines.append(f"| ✅ 字段完全匹配 | {total_clean} |")
lines.append(f"| ❌ 实际不匹配 | {total_issues} |")
lines.append(f"| ⚠️ 已知跳过 | {total_skip} |")
lines.append(f"| 基类/配置 | {len(spiders) - total_data - total_skip} |")
lines.append(f"| **合计** | **{len(spiders)}** |")

with open(REPORT_PATH, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f"Report: {REPORT_PATH}")
print(f"Clean: {total_clean}")
print(f"Issues: {total_issues}")
print(f"Skip: {total_skip}")
print(f"Base: {len(spiders) - total_data - total_skip}")
print(f"Total: {len(spiders)}")
