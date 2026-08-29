"""批量运行所有蜘蛛，超时30秒/个，采集结果报告"""
import subprocess, sys, os, json, time

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 获取所有 spider name
result = subprocess.run([sys.executable, "-m", "scrapy", "list"], capture_output=True, text=True)
all_spiders = [s.strip() for s in result.stdout.strip().split('\n') if s.strip()]

print(f"Total spiders: {len(all_spiders)}")
print(f"{'='*80}")

results = []
passed = 0
failed = 0
timeout = 0
no_data = 0

for i, spider in enumerate(all_spiders):
    print(f"[{i+1}/{len(all_spiders)}] {spider}...", end=" ", flush=True)
    start = time.time()
    try:
        r = subprocess.run(
            [sys.executable, "-m", "scrapy", "crawl", spider,
             "-a", "start_page=1", "-a", "end_page=1"],
            capture_output=True, text=True, timeout=45
        )
        elapsed = time.time() - start
        out = r.stdout + r.stderr

        items = "0"
        drops = "0"
        errs = "0"
        status_200 = "0"
        for line in out.split('\n'):
            if "item_scraped_count" in line:
                items = line.strip().split(": ")[-1].rstrip(",").strip("'")
            if "item_dropped_count" in line:
                drops = line.strip().split(": ")[-1].rstrip(",").strip("'")
            if "log_count/ERROR" in line:
                errs = line.strip().split(": ")[-1].rstrip(",").strip("'")
            if "response_status_count/200" in line:
                status_200 = line.strip().split(": ")[-1].rstrip(",").strip("'")

        items_i = int(items) if items.isdigit() else 0
        drops_i = int(drops) if drops.isdigit() else 0
        errs_i = int(errs) if errs.isdigit() else 0

        if items_i > 0 and drops_i == 0:
            status = "OK"
            passed += 1
        elif items_i > 0:
            status = "PARTIAL"
            failed += 1
        elif items_i == 0 and drops_i > 0:
            status = "DROPPED"
            failed += 1
        else:
            status = "NO_DATA"
            no_data += 1

        results.append((spider, status, items_i, drops_i, errs_i, f"{elapsed:.1f}s"))
        print(f"{status} items={items_i} drops={drops_i} errors={errs_i} {elapsed:.1f}s")

    except subprocess.TimeoutExpired:
        timeout += 1
        results.append((spider, "TIMEOUT", 0, 0, 0, "45s"))
        print("TIMEOUT")
    except Exception as e:
        no_data += 1
        results.append((spider, "ERROR", 0, 0, 0, "0s"))
        print(f"ERROR: {e}")

print(f"\n{'='*80}")
print(f"SUMMARY: OK={passed} FAIL={failed} TIMEOUT={timeout} NO_DATA={no_data} TOTAL={len(all_spiders)}")

# 写入报告
report_path = os.path.join("docs", "spider_test_report.txt")
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(f"爬虫测试报告 | {time.strftime('%Y-%m-%d %H:%M')}\n")
    f.write(f"{'='*80}\n\n")
    f.write(f"{'Spider':<40s} {'Status':<10s} {'Items':>6s} {'Drops':>6s} {'Errors':>6s} {'Time':>8s}\n")
    f.write(f"{'-'*80}\n")
    for spider, status, items, drops, errs, elapsed in results:
        f.write(f"{spider:<40s} {status:<10s} {items:>6d} {drops:>6d} {errs:>6d} {elapsed:>8s}\n")
    f.write(f"{'-'*80}\n")
    f.write(f"OK: {passed}  FAIL: {failed}  TIMEOUT: {timeout}  NO_DATA: {no_data}  TOTAL: {len(all_spiders)}\n")

print(f"\nReport: {report_path}")
