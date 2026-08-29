import json
import requests
from tenacity import Retrying, stop_after_attempt

from config import LLM_CONF as LLM_SERVER


class CustomLlmChat(object):
    def __init__(self, **kwargs):
        self.host = LLM_SERVER.get('host', "")
        # self.model = LLM_SERVER.get('model', "Qwen/Qwen3-4B")
        self.model = "Qwen/Qwen3-4B"

    def chat(self, now_code, company_name, **kwargs):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.host}"
        }

        prompt = f"""
                请查询股票代码 {now_code} {company_name}退市前的股票代码。

                只返回 JSON，不要解释，不要 Markdown。

                返回格式必须是：
                {{
                  "now_code": "{now_code}",
                  "old_code": "查询到的退市前股票代码"
                }}

                如果无法确定，old_code 返回空字符串。
                """
        messages = [
            {
                "role": "system",
                "content": "你是一个股票代码查询助手，只返回严格 JSON。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            **kwargs  # 支持 temperature, max_tokens 等
        }

        for attempt in Retrying(stop=stop_after_attempt(3)):
            with attempt:
                response = requests.post(
                    self.host,
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=60
                )
                response.raise_for_status()  # 抛出 HTTP 错误
                result = response.json()
                if "choices" not in result or len(result["choices"]) == 0:
                    raise ValueError("Invalid response structure")
                return result["choices"][0]["message"]["content"]
