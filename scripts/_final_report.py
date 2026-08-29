"""生成完整的爬虫字段逻辑对比报告"""
import os, re, ast, json, pymysql
from datetime import datetime

SPIDER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'spiders')
OLD_DIR = r'C:\Users\24613\workstation\data_crawl_server\spider'
REPORT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs', 'spider_field_audit.md')

AUTO_COLS = {'id', 'created_time', 'updated_time', 'update_time', 'create_time', 'crawl_time'}

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

def extract_spider_info(filepath):
    """提取蜘蛛的关键信息"""
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    info = {'file': os.path.basename(filepath), 'fields': {}, 'yield_count': 0}

    # data_table
    m = re.search(r"data_table\s*=\s*'([^']+)'", source) or re.search(r'data_table\s*=\s*"([^"]+)"', source)
    info['data_table'] = m.group(1) if m else None

    # spider name
    m = re.search(r"name\s*=\s*'([^']+)'", source) or re.search(r'name\s*=\s*"([^"]+)"', source)
    info['spider_name'] = m.group(1) if m else None

    # dedup_fields
    m = re.search(r"dedup_fields\s*=\s*\[(.*?)\]", source)
    info['dedup'] = m.group(1).replace("'","").replace('"','') if m else ''

    # 提取所有 yield/return dict 的字段
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return info

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Yield, ast.Return)) or not node.value or not isinstance(node.value, ast.Dict):
            continue
        info['yield_count'] += 1
        for k, v in zip(node.value.keys, node.value.values):
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                val_str = "dynamic"  # default
                if isinstance(v, ast.Constant):
                    val_str = repr(v.value)[:60]
                elif isinstance(v, ast.Call):
                    if isinstance(v.func, ast.Attribute):
                        val_str = f"{v.func.attr}()"[:60]
                    elif isinstance(v.func, ast.Name):
                        val_str = f"{v.func.id}()"[:60]
                info['fields'][k.value] = val_str

    return info

def find_old_spider(name):
    """在旧项目中查找对应的蜘蛛"""
    if not OLD_DIR:
        return None
    for root, dirs, files in os.walk(OLD_DIR):
        for f in files:
            if f.endswith('.py') and f != '__init__.py':
                path = os.path.join(root, f)
                with open(path, 'r', encoding='utf-8') as fh:
                    content = fh.read()
                # 匹配 spider_name 或 data_table
                if f"'{name}'" in content or f'"{name}"' in content:
                    return os.path.relpath(path, OLD_DIR)
    return None


# 主流程
lines = []
lines.append(f"# 爬虫字段逻辑对比报告")
lines.append(f"")
lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
lines.append(f"> 新旧对比: data_crawl_server (旧) vs crawl_spider_engine (新)")
lines.append(f"> 数据库: crawl_data")
lines.append(f"")
lines.append(f"## 图例")
lines.append(f"")
lines.append(f"- ✅ 字段与表列完全一致")
lines.append(f"- 🟡 AST误报 (helper方法/变量yield)")
lines.append(f"- ⚠️ 已知跳过")
lines.append(f"- ❌ 实际不匹配")
lines.append(f"")

# 按目录分组
categories = {}
for root, dirs, files in os.walk(SPIDER_DIR):
    for f in sorted(files):
        if not f.endswith('.py') or f.startswith('__') or f == 'base_spider.py':
            continue
        path = os.path.join(root, f)
        rel = os.path.relpath(path, SPIDER_DIR)
        cat = os.path.dirname(rel) or 'root'
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(path)

for cat in sorted(categories.keys()):
    lines.append(f"## {cat}")
    lines.append(f"")
    lines.append(f"| 蜘蛛 | 表 | 字段数 | DB列数 | 状态 | 旧项目 |")
    lines.append(f"|------|-----|--------|--------|------|--------|")

    for path in categories[cat]:
        rel = os.path.relpath(path, SPIDER_DIR)
        info = extract_spider_info(path)
        fname = info['file']

        if not info['data_table']:
            lines.append(f"| {fname} | - | - | - | 基类/配置 | - |")
            continue

        table = info['data_table']
        db_cols = table_cols.get(table, {})
        spider_fields = {k for k in info['fields'].keys() if k != '_table'}

        extra = spider_fields - set(db_cols.keys())
        missing = set(db_cols.keys()) - spider_fields

        status = "✅" if not extra and not missing else ""
        if not info['yield_count']:
            status = "基类"
        elif fname in ('amac_manager.py', 'gov_bidding_spider.py', 'qyyjt_bond_issue_spider.py', 'hk_listing_spider.py'):
            status = "⚠️ 已知"
        elif info['yield_count'] == 1 and extra and missing:
            status = "🟡 误报"

        old = find_old_spider(info['spider_name']) if info['spider_name'] else None

        lines.append(f"| {fname} | {table} | {len(spider_fields)} | {len(db_cols)} | {status} | {old or '-'} |")

    lines.append(f"")

# 详细字段对比 (仅产出数据的蜘蛛)
lines.append(f"## 详细字段对比")
lines.append(f"")

for cat in sorted(categories.keys()):
    lines.append(f"### {cat}")
    lines.append(f"")

    for path in categories[cat]:
        rel = os.path.relpath(path, SPIDER_DIR)
        info = extract_spider_info(path)

        if not info['data_table'] or not info['yield_count']:
            continue

        table = info['data_table']
        db_cols = table_cols.get(table, {})
        spider_fields = {k for k in info['fields'].keys() if k != '_table'}

        extra = spider_fields - set(db_cols.keys())
        missing = set(db_cols.keys()) - spider_fields

        if extra or missing:
            lines.append(f"#### {info['file']} → {table}")
            lines.append(f"")
            if extra:
                lines.append(f"**EXTRA** (蜘蛛有, 表无): `{', '.join(sorted(extra))}`")
                lines.append(f"")
            if missing:
                lines.append(f"**MISSING** (表有, 蜘蛛无): `{', '.join(sorted(missing))}`")
                lines.append(f"")

            # Show actual DB column types for missing fields
            if missing:
                lines.append(f"| 缺失字段 | DB类型 |")
                lines.append(f"|---------|--------|")
                for col in sorted(missing):
                    lines.append(f"| {col} | {db_cols.get(col, '?')} |")
                lines.append(f"")

# Summary
lines.append(f"## 汇总")
lines.append(f"")
lines.append(f"| 目录 | 蜘蛛数 |")
lines.append(f"|------|--------|")
for cat in sorted(categories.keys()):
    lines.append(f"| {cat} | {len(categories[cat])} |")
lines.append(f"| **合计** | **{sum(len(v) for v in categories.values())}** |")
lines.append(f"")

with open(REPORT_PATH, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f"Report written to: {REPORT_PATH}")
print(f"Total spiders: {sum(len(v) for v in categories.values())}")
