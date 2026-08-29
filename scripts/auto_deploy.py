#!/usr/bin/env python3
"""Git 变更自检测 — 发现新提交自动 egg 打包 + Scrapyd 热部署，不中断运行中 Job"""
import subprocess, os, sys, time, glob, json, shutil
import urllib.request

CHECK_INTERVAL = int(os.environ.get('AUTO_DEPLOY_INTERVAL', '30'))
SCRAPYD_URL = os.environ.get('SCRAPYD_URL', 'http://localhost:6800')
PROJECT = os.environ.get('SCRAPYD_PROJECT', 'crawl_spider_engine')
ENGINE_DIR = os.environ.get('ENGINE_DIR', '/app')


def log(msg: str):
    print(f'[auto_deploy] {msg}', flush=True)


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=kw.pop('timeout', 60), **kw)


def get_head_commit():
    try:
        r = _run(['git', '-C', ENGINE_DIR, 'rev-parse', 'HEAD'])
        return r.stdout.strip() if r.returncode == 0 else ''
    except Exception:
        return ''


def deploy():
    """打包 egg 并热部署到 Scrapyd"""
    log('检测到新提交，开始热部署...')
    try:
        # 清理旧构建
        for d in [os.path.join(ENGINE_DIR, p) for p in ['build', 'dist']]:
            if os.path.isdir(d):
                shutil.rmtree(d, ignore_errors=True)
        for p in glob.glob(os.path.join(ENGINE_DIR, '*.egg-info')):
            shutil.rmtree(p, ignore_errors=True)

        # 打包 egg
        r = _run(['python', 'setup.py', 'bdist_egg'], cwd=ENGINE_DIR, timeout=120)
        if r.returncode != 0:
            log(f'egg 打包失败: {r.stderr[-500:]}')
            return False

        eggs = sorted(glob.glob(os.path.join(ENGINE_DIR, 'dist', '*.egg')), key=os.path.getmtime)
        if not eggs:
            log('未找到 egg 文件')
            return False

        # 上传
        egg_path = eggs[-1]
        import http.client
        import mimetypes

        boundary = '----WebKitFormBoundary' + os.urandom(16).hex()
        version = time.strftime('%Y%m%d%H%M%S')

        with open(egg_path, 'rb') as f:
            egg_data = f.read()

        body = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="project"\r\n\r\n{PROJECT}\r\n'
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="version"\r\n\r\n{version}\r\n'
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="egg"; filename="{os.path.basename(egg_path)}"\r\n'
            f'Content-Type: application/octet-stream\r\n\r\n'
        ).encode() + egg_data + f'\r\n--{boundary}--\r\n'.encode()

        req = urllib.request.Request(
            f'{SCRAPYD_URL}/addversion.json',
            data=body,
            headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
        )
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())

        if result.get('status') == 'ok':
            spiders = result.get('spiders', '?')
            log(f'热部署成功 version={version} spiders={spiders}')
            return True
        else:
            log(f'Scrapyd 响应异常: {result}')
            return False

    except Exception as e:
        log(f'部署失败: {e}')
        return False


def main():
    log(f'启动, 检测间隔={CHECK_INTERVAL}s, Scrapyd={SCRAPYD_URL}')

    last_commit = get_head_commit()
    if not last_commit:
        log('警告: 无法读取 git commit，等待下次检测')
    else:
        log(f'当前 HEAD: {last_commit[:12]}')

    while True:
        time.sleep(CHECK_INTERVAL)
        try:
            current = get_head_commit()
            if current and current != last_commit:
                log(f'新提交: {last_commit[:12]} → {current[:12]}')
                if deploy():
                    last_commit = current
        except Exception as e:
            log(f'检测异常: {e}')


if __name__ == '__main__':
    main()
