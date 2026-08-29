"""Playwright 脚本：打开 cneptp.com 登录页，等待用户完成 SMS 登录后捕获 xj-token
使用方法: python tmp_get_cneptp_token.py
完成登录后关闭浏览器窗口，token 将输出到控制台并保存到文件
"""
import time, json, sys, os
from playwright.sync_api import sync_playwright

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), 'cneptp_token.txt')

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/146.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        # 直接打开登录页
        print('打开 cneptp.com 登录页...')
        page.goto('https://www.cneptp.com/login', wait_until='networkidle', timeout=30000)
        page.wait_for_timeout(2000)

        # 可能需要点击登录按钮
        try:
            login_btn = page.locator('text=登录').first
            if login_btn.is_visible():
                login_btn.click()
                page.wait_for_timeout(2000)
        except:
            pass

        print(f'当前页面: {page.url}')
        print(f'页面标题: {page.title()}')
        print()
        print('=' * 60)
        print('请在浏览器中完成 SMS 登录（手机号 + 验证码）')
        print('登录成功后，关闭浏览器窗口或等待自动检测')
        print('=' * 60)

        # 每 2 秒检查一次是否有 xj-token
        token = None
        for i in range(180):
            time.sleep(2)
            cookies = context.cookies()
            for c in cookies:
                if c['name'] == 'xj-token':
                    token = c['value']
                    break
            if token:
                break
            # 也检查 user-token 的变化（可能有新token）
            if i % 15 == 0 and i > 0:
                print(f'  等待中... ({i*2}s) 当前 cookies: {[c["name"] for c in cookies[:5]]}')

        if token:
            print(f'\n成功获取 xj-token:')
            print(f'{token}')
            # 保存到文件
            with open(OUTPUT_FILE, 'w') as f:
                f.write(token)
            print(f'\nToken 已保存到: {OUTPUT_FILE}')
        else:
            print('\n未获取到 xj-token。请检查是否登录成功。')
            # 输出所有 cookie 供调试
            cookies = context.cookies()
            print(f'当前 cookies ({len(cookies)}):')
            for c in cookies:
                print(f'  {c["name"]} = {c["value"][:80]}')

        browser.close()

if __name__ == '__main__':
    main()
