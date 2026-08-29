"""批量运行蜘蛛 - 通过stats准确判断采集结果"""
import subprocess, sys, os, time, re

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

result = subprocess.run([sys.executable, "-m", "scrapy", "list"], capture_output=True, text=True)
all_spiders = [s.strip() for s in result.stdout.strip().split('\n') if s.strip()]

print(f"Total: {len(all_spiders)}")
print(f"{'Spider':<45s} {'Status':<10s} {'Items':>5s} {'Drops':>5s} {'Reqs':>4s} {'200':>4s} {'Time':>6s}")
print("-" * 90)

results = []
stats = {"OK": 0, "NO_DATA": 0, "NO_API": 0, "DROPPED": 0, "TIMEOUT": 0, "ERROR": 0}

for i, spider in enumerate(all_spiders):
    start = time.time()
    try:
        r = subprocess.run(
            [sys.executable, "-m", "scrapy", "crawl", spider,
             "-a", "start_page=1", "-a", "end_page=1"],
            capture_output=True, text=True, timeout=60
        )
        elapsed = time.time() - start
        out = r.stdout + r.stderr

        # 提取stats
        def get_stat(key):
            m = re.search(rf"'{key}':\s*(\d+)", out)
            return int(m.group(1)) if m else 0

        items = get_stat('item_scraped_count')
        drops = get_stat('item_dropped_count')
        reqs = get_stat('downloader/request_count')
        http200 = get_stat('downloader/response_status_count/200')
        errors = get_stat('log_count/ERROR')
        finish = "finished" if "finish_reason': 'finished'" in out else "other"

        # 判断状态
        if items > 0 and drops == 0:
            status = "OK"
        elif items > 0 and drops > 0:
            status = "DROPPED"
        elif http200 == 0 or reqs <= 1:
            status = "NO_API"
        elif items == 0 and http200 > 1:
            status = "NO_DATA"
        else:
            status = "NO_API"

        stats[status] = stats.get(status, 0) + 1
        results.append((spider, status, items, drops, reqs, http200, f"{elapsed:.1f}s"))

        icon = {"OK": "+", "NO_DATA": "-", "NO_API": "x", "DROPPED": "!", "TIMEOUT": "T", "ERROR": "E"}.get(status, "?")
        print(f"[{i+1:3d}] {spider:<40s} {icon} {status:<7s} {items:>5d} {drops:>5d} {reqs:>4d} {http200:>4d} {elapsed:>5.1f}s")

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        stats["TIMEOUT"] += 1
        results.append((spider, "TIMEOUT", 0, 0, 0, 0, "60s"))
        print(f"[{i+1:3d}] {spider:<40s} T TIMEOUT")

    except Exception as e:
        stats["ERROR"] += 1
        results.append((spider, "ERROR", 0, 0, 0, 0, "0s"))
        print(f"[{i+1:3d}] {spider:<40s} E ERROR: {str(e)[:30]}")

# Summary
print(f"\n{'='*90}")
print(f"OK: {stats['OK']}  NO_DATA: {stats['NO_DATA']}  NO_API: {stats['NO_API']}  DROPPED: {stats['DROPPED']}  TIMEOUT: {stats['TIMEOUT']}  ERROR: {stats['ERROR']}")
print(f"Total: {len(all_spiders)}")

# Write report
rp = os.path.join("docs", "spider_test_report.txt")
with open(rp, 'w', encoding='utf-8') as f:
    f.write(f"爬虫测试报告 | {time.strftime('%Y-%m-%d %H:%M')}\n{'='*80}\n\n")
    f.write(f"{'Spider':<45s} {'Status':<8s} {'Items':>6s} {'Drops':>6s} {'Reqs':>5s} {'200':>5s} {'Time':>7s}\n{'-'*85}\n")
    for spider, status, items, drops, reqs, http200, elapsed in results:
        f.write(f"{spider:<45s} {status:<8s} {items:>6d} {drops:>6d} {reqs:>5d} {http200:>5d} {elapsed:>7s}\n")
    f.write(f"{'-'*85}\n")
    f.write(f"OK:{stats['OK']} NO_DATA:{stats['NO_DATA']} NO_API:{stats['NO_API']} DROPPED:{stats['DROPPED']} TIMEOUT:{stats['TIMEOUT']} ERROR:{stats['ERROR']}\n")

print(f"Report: {rp}")
