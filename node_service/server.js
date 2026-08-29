/**
 * Crawl Spider Engine — Node.js 辅助服务
 * 端口 3000（与 admin_web 不冲突时可独立运行）
 *
 * 端点：
 *   POST /exec_jsc   — 执行 JS 代码（JSL 521 中间件使用）
 *   POST /rs_ts      — RS 412 绕过（nmpa.gov.cn）
 *   POST /rs_cookie  — 平台 Cookie 生成（pbc 等）
 *   GET  /health     — 健康检查
 */
const express = require('express');
const { JSDOM } = require('jsdom');
const axios = require('axios');
const app = express();

app.use(express.json({ limit: '5mb' }));
app.use(express.urlencoded({ extended: true }));

const PORT = process.env.PORT || 3000;

// ─── 健康检查 ──────────────────────────────────────────────────

app.get('/health', (req, res) => {
    res.json({ status: 'ok', uptime: process.uptime() });
});

// ─── 执行 JS 代码（JSL 521 加速乐中间件）─────────────────────

app.post('/exec_jsc', async (req, res) => {
    const { code, params } = req.body || {};
    if (!code) return res.status(400).json({ error: 'code is required' });

    try {
        const pageUrl = (params && params.url && params.url.startsWith('http')) ? params.url : 'https://www.example.com/';
        const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', {
            url: pageUrl,
            referrer: (params && params.referrer) || '',
            runScripts: 'dangerously',
            resources: 'usable',
        });
        // 注入常用全局变量
        global.window = dom.window;
        global.document = dom.window.document;
        global.navigator = dom.window.navigator;
        global.location = dom.window.location;

        const result = dom.window.eval(code);
        // 收集 cookies
        const cookies = [];
        for (const cookie of dom.window.document.cookie.split(';')) {
            const [name, ...rest] = cookie.trim().split('=');
            if (name) cookies.push({ name, value: rest.join('=') });
        }

        res.json({ result: result, cookies, success: true });
    } catch (e) {
        res.json({ error: e.message, success: false });
    }
});

// ─── RS 412 绕过（nmpa.gov.cn）──────────────────────────────

app.post('/rs_ts', async (req, res) => {
    const { script, params } = req.body || {};
    // 兼容 NodeClient.exec_ts() 格式: {script: 'rs_decrypt', params: {...}}
    const p = params || req.body || {};
    const meta_content = p.meta_content || '';
    const ts_code = p.ts_code || '';
    const link_code = p.link_code || '';
    const website_info = p.website_info || {};

    if (!meta_content || !ts_code) {
        return res.json({ value: {}, success: false, error: 'meta_content and ts_code required' });
    }

    try {
        // 构建 RS challenge 页面
        const html = `<!DOCTYPE html><html><head>
            <meta charset="utf-8">
            <meta content="${meta_content.replace(/"/g, '&quot;')}" r="m">
            <script>${ts_code}</script>
            ${link_code ? `<script src="${link_code}"></script>` : ''}
        </head><body></body></html>`;

        const dom = new JSDOM(html, {
            url: (website_info && website_info.href) || 'https://www.nmpa.gov.cn',
            runScripts: 'dangerously',
            resources: 'usable',
        });

        // 等待脚本执行
        await new Promise(resolve => setTimeout(resolve, 2000));

        // 收集 cookies
        const cookies = {};
        const cookieStr = dom.window.document.cookie;
        if (cookieStr) {
            cookieStr.split(';').forEach(c => {
                const [name, ...rest] = c.trim().split('=');
                if (name) cookies[name] = rest.join('=');
            });
        }

        // 也尝试从 JSDOM cookie jar 获取
        try {
            const jar = dom.window.document._cookieJar;
            if (jar) {
                const serialized = jar.getCookieStringSync((website_info && website_info.href) || 'https://www.nmpa.gov.cn');
                serialized.split(';').forEach(c => {
                    const [name, ...rest] = c.trim().split('=');
                    if (name && !cookies[name]) cookies[name] = rest.join('=');
                });
            }
        } catch (_) {}

        res.json({ value: cookies, success: Object.keys(cookies).length > 0 });
    } catch (e) {
        console.error('RS bypass error:', e.message);
        res.json({ value: {}, success: false, error: e.message });
    }
});

// ─── 平台 Cookie 生成 ──────────────────────────────────────

app.post('/rs_cookie', async (req, res) => {
    const { platform, params } = req.body || {};

    try {
        if (platform === 'pbc') {
            // 人民银行：直接访问首页获取初始 cookie
            const resp = await axios.get('https://www.pbc.gov.cn/', {
                headers: {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,*/*',
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                },
                maxRedirects: 5,
                timeout: 15000,
            });
            const cookies = {};
            if (resp.headers['set-cookie']) {
                resp.headers['set-cookie'].forEach(c => {
                    const [nv] = c.split(';');
                    const [name, ...rest] = nv.split('=');
                    if (name) cookies[name] = rest.join('=');
                });
            }
            res.json({ cookies, success: true });
        } else {
            // 通用：用 JSDOM 获取 cookie
            const url = (params && params.url) || 'https://www.baidu.com';
            const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', {
                url, runScripts: 'dangerously',
            });
            res.json({ cookies: {}, success: true, platform });
        }
    } catch (e) {
        console.error(`Cookie error for ${platform}:`, e.message);
        res.json({ cookies: {}, success: false, error: e.message });
    }
});

// ─── 启动 ────────────────────────────────────────────────────

app.listen(PORT, '0.0.0.0', () => {
    console.log(`[NodeService] Listening on port ${PORT}`);
    console.log(`[NodeService] Endpoints: /exec_jsc /rs_ts /rs_cookie /health`);
});
