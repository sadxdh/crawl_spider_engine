import subprocess
import sys

if __name__ == '__main__':
    cmd = [
        sys.executable, '-m', 'scrapy', 'crawl', 'law_regulation_samr_rules'
        # ,'-a', 'start_page=1', '-a', 'end_page=2'
        ]
    try:
        subprocess.run(cmd, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"执行失败: {e}")
        sys.exit(1)
