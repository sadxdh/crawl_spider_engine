"""
LLM 服务客户端 - 用于内容抽取
使用 OpenAI-compatible API (Qwen/Qwen3-1.7B)
"""
import json
from openai import OpenAI
from loguru import logger
from config import LLM_CONF


class LLMClient:
    """LLM 内容抽取客户端（单例）"""
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        host = LLM_CONF.get('host', '')
        api_key = LLM_CONF.get('api_key', 'lm-studio')
        if not host:
            logger.warning("[LLMClient] LLM host 未配置，LLM功能不可用")
            self._client = None
            return
        # OpenAI 兼容接口（去掉末尾 /chat/completions）
        base_url = host.replace('/chat/completions', '').rstrip('/')
        self._client = OpenAI(base_url=base_url, api_key=api_key)
        logger.info(f"[LLMClient] 初始化: {base_url}")

    @property
    def model(self) -> str:
        return LLM_CONF.get('model', 'Qwen/Qwen3-1.7B')

    def extract(self, content: str, schema: dict, system_prompt: str = None) -> dict:
        """
        使用 LLM 从文本中抽取结构化数据

        Args:
            content: 待抽取的文本内容
            schema: 期望的输出 JSON Schema
            system_prompt: 自定义系统提示（可选）

        Returns:
            抽取出的结构化数据字典
        """
        if not self._client:
            raise RuntimeError("LLM 客户端未初始化（host 未配置）")

        default_system = (
            "你是一个专业的数据抽取助手。根据用户提供的文本，"
            "按照要求的 JSON 格式抽取信息。只输出 JSON，不要其他内容。"
        )
        messages = [
            {"role": "system", "content": system_prompt or default_system},
            {"role": "user", "content": f"Schema: {json.dumps(schema, ensure_ascii=False)}\n\n待抽取文本:\n{content}"},
        ]

        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_tokens=2048,
            )
            raw = resp.choices[0].message.content.strip()
            # 清理 markdown 代码块
            if raw.startswith('```'):
                raw = raw.split('```')[1]
                if raw.startswith('json'):
                    raw = raw[4:]
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning(f"[LLMClient] JSON解析失败: {e}")
            return {}
        except Exception as e:
            logger.error(f"[LLMClient] 调用失败: {e}")
            raise

    def summarize(self, content: str, max_length: int = 200) -> str:
        """生成文本摘要"""
        if not self._client:
            return content[:max_length]
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "请对以下文本生成简洁摘要，不超过200字。"},
                    {"role": "user", "content": content},
                ],
                temperature=0.3,
                max_tokens=300,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"[LLMClient] summarize 失败: {e}")
            return content[:max_length]


llm_client = LLMClient()
