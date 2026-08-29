"""全量蜘蛛测试 - 完整链路验证，结果写入报告"""
import subprocess, sys, os, re, time, pymysql

BASE = r'C:/Users/24613/workstation/crawl_spider_engine'
os.chdir(BASE)

# 1. 获取所有蜘蛛
r = subprocess.run([sys.executable, '-m', 'scrapy', 'list'],
                   capture_output=True, text=True, timeout=60, cwd=BASE)
spiders = [s.strip() for s in r.stdout.strip().split('\n') if s.strip() and s[0].isalpha()]
print(f'SPIDERS: {len(spiders)}')

# 2. 逐个测试
ok = no_data = no_api = dropped = timeout = err_count = 0
results = []

for i, spider in enumerate(spiders):
    t0 = time.time()
    its = dr = rq = s200 = 0
    try:
        rr = subprocess.run(
            [sys.executable, '-m', 'scrapy', 'crawl', spider,
             '-a', 'start_page=1', '-a', 'end_page=1'],
            capture_output=True, text=True, timeout=60, cwd=BASE
        )
        elapsed = time.time() - t0
        out = rr.stdout + rr.stderr
        for pat, var in [("item_scraped_count", "its"), ("item_dropped_count", "dr"),
                          ("request_count", "rq"), ("response_status_count/200", "s200")]:
            m = re.search(rf"'{pat}':\s*(\d+)", out)
            if m: exec(f"{var} = int(m.group(1))")

        if its > 0 and dr == 0: st = '+'; ok += 1
        elif its > 0: st = '!'; dropped += 1
        elif rq <= 1: st = 'x'; no_api += 1
        else: st = '-'; no_data += 1

    except subprocess.TimeoutExpired:
        elapsed = 60; st = 'T'; timeout += 1
    except Exception:
        elapsed = time.time() - t0; st = 'E'; err_count += 1

    line = f'{st} {spider:<45s} items={its:>4d} drops={dr:>4d} reqs={rq:>3d} 200={s200:>3d} {elapsed:>5.0f}s'
    results.append(line)
    print(f'[{i+1:3d}] {line}')

# 3. DB验证
conn = pymysql.connect(host='py.w.com', user='root', password='IK29lKb0',
                        database='crawl_data', charset='utf8mb4',
                        cursorclass=pymysql.cursors.DictCursor)
db_results = {}
with conn.cursor() as cur:
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='crawl_data' AND update_time > DATE_SUB(NOW(), INTERVAL 2 HOUR)")
    for r in cur.fetchall():
        t = r['table_name']
        cur.execute(f"SELECT COUNT(*) as cnt FROM `{t}` WHERE created_time > DATE_SUB(NOW(), INTERVAL 2 HOUR)")
        cnt = cur.fetchone()['cnt']
        if cnt > 0:
            db_results[t] = cnt
conn.close()

# 4. 写入报告
with open(os.path.join(BASE, 'docs', 'spider_test_report.txt'), 'w', encoding='utf-8') as f:
    f.write(f'Spider Test Report | {time.strftime("%Y-%m-%d %H:%M")}\n')
    f.write(f'{"="*80}\n\n')
    for line in results:
        f.write(line + '\n')
    f.write(f'\n{"="*80}\n')
    f.write(f'+ OK:{ok}  ! DROPPED:{dropped}  - NO_DATA:{no_data}  x NO_API:{no_api}  T TIMEOUT:{timeout}  E ERROR:{err_count}\n')
    f.write(f'TOTAL: {len(spiders)}\n\n')
    if db_results:
        f.write(f'DB writes confirmed (last 2h):\n')
        for t, cnt in sorted(db_results.items()):
            f.write(f'  {t}: {cnt} rows\n')

print(f'\n+ {ok}  ! {dropped}  - {no_data}  x {no_api}  T {timeout}  E {err_count}')
print(f'Report: docs/spider_test_report.txt')
