"""
Playwright 页面抓取工具 - 用于绕过 WAF (如 nmpa 412, pbc cookie 验证)
在 Scrapy 容器中安装 playwright 后使用:
  pip install playwright && playwright install chromium
"""
import asyncio
from loguru import logger


async def fetch_with_browser(url: str, headers: dict = None, timeout: int = 30) -> dict:
    """使用 Playwright Chromium 抓取页面，返回 {html, cookies, status}"""
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
        )
        ctx = await browser.new_context(
            user_agent=headers.get('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36') if headers else None,
        )
        page = await ctx.new_page()
        try:
            resp = await page.goto(url, wait_until='networkidle', timeout=timeout * 1000)
            status = resp.status if resp else 0
            html = await page.content()
            cookies = await ctx.cookies()
            await browser.close()
            return {'html': html, 'cookies': cookies, 'status': status, 'url': page.url}
        except Exception as e:
            await browser.close()
            logger.error(f'[PlaywrightFetcher] {url}: {e}')
            return {'html': '', 'cookies': [], 'status': 0, 'url': url, 'error': str(e)}


def fetch_sync(url: str, headers: dict = None, timeout: int = 30) -> dict:
    """同步包装器"""
    return asyncio.run(fetch_with_browser(url, headers, timeout))
