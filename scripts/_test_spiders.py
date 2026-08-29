"""批量测试蜘蛛，报告采集结果"""
import subprocess, sys, os, json

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SPIDERS = [
    # 税局 POST API
    ("report_tax_anhui", "POST XML"),
    ("report_tax_dalian", "POST XML"),
    ("report_tax_jiangsu", "POST XML"),
    ("report_tax_shanghai", "POST XML"),
    # 税局 GET HTML
    ("report_tax_guangxi", "GET HTML"),
    ("report_tax_hainan", "GET HTML"),
    # 税局 特殊API
    ("report_tax_fujian", "POST JSON"),
    ("report_tax_guangdong", "POST JSON"),
    # 非税局
    ("finance_trust_finance", "JSON API"),
    ("economy_jggg_land", "GET HTML"),
    ("report_debt_finance", "POST JSON"),
]

for spider, typ in SPIDERS:
    try:
        r = subprocess.run(
            [sys.executable, "-m", "scrapy", "crawl", spider,
             "-a", "start_page=1", "-a", "end_page=1"],
            capture_output=True, text=True, timeout=45
        )
        out = r.stdout + r.stderr
        items = ""
        drops = ""
        errs = ""
        status = ""
        for line in out.split('\n'):
            if "item_scraped_count" in line:
                items = line.strip().split(": ")[-1].rstrip(",")
            if "item_dropped_count" in line:
                drops = line.strip().split(": ")[-1].rstrip(",")
            if "log_count/ERROR" in line:
                errs = line.strip().split(": ")[-1].rstrip(",")
            if "finish_reason" in line:
                status = line.strip().split(": ")[-1].strip("',")
        result = "OK" if items and int(items) > 0 and (not drops or int(drops) == 0) else ""
        if not result:
            if status == "finished" and not items or items == "0":
                result = "NO_DATA"
            elif "closed" in out or "shutdown" in out:
                result = "CLOSED"
        print(f"{spider:35s} [{typ:10s}] items={items or '0':>3s} drops={drops or '0':>3s} errors={errs or '0':>2s} {result}")
    except subprocess.TimeoutExpired:
        print(f"{spider:35s} [{typ:10s}] TIMEOUT")
    except Exception as e:
        print(f"{spider:35s} [{typ:10s}] ERROR: {e}")
