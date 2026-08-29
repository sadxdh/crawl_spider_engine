import json
import requests
from tenacity import Retrying, stop_after_attempt

from config import LLM_CONF as LLM_SERVER


class CustomLlmChat(object):
    def __init__(self, **kwargs):
        self.host = LLM_SERVER.get('host', "")
        # self.model = LLM_SERVER.get('model', "Qwen/Qwen3-4B")
        self.model = "Qwen/Qwen3-4B"

    def chat(self, prompt, text, **kwargs):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.host}"
        }

        messages = [
            {"role": "system", "content": "资深法律数据分析专家"},
            {"role": "user", "content": prompt + '\n' + text}
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
