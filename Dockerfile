FROM python:3.11-slim

WORKDIR /app

RUN sed -i 's/deb.debian.org/mirrors.cloud.aliyuncs.com/g' /etc/apt/sources.list.d/debian.sources

RUN apt-get update && apt-get install -y \
    gcc default-libmysqlclient-dev pkg-config curl xz-utils \
    libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Node.js (qzd_sign / RS WAF)
RUN curl -fsSL https://nodejs.org/dist/v22.11.0/node-v22.11.0-linux-x64.tar.gz \
    -o /tmp/node.tar.gz && tar -xzf /tmp/node.tar.gz -C /tmp \
    && cp -r /tmp/node-v22.11.0-linux-x64/* /usr/local/ \
    && rm -rf /tmp/node.tar.gz /tmp/node-v22.11.0-linux-x64

COPY requirements.txt .
RUN pip install --no-cache-dir scrapyd==1.6.0 setuptools -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN playwright install --with-deps chromium 2>/dev/null || true

COPY . .

RUN mkdir -p /var/lib/scrapyd/eggs /var/lib/scrapyd/logs /var/lib/scrapyd/dbs /engine/config \
    && chmod +x /app/entrypoint.sh

ENV CURRENT_ENV=prod PYTHONUNBUFFERED=1 TZ=Asia/Shanghai
EXPOSE 6800

HEALTHCHECK --interval=30s CMD curl -sf http://localhost:6800/daemonstatus.json
ENTRYPOINT ["/app/entrypoint.sh"]
