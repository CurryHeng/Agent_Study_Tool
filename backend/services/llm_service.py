"""LLM 统一调用封装（详细设计 Pt.3 §16）。

所有模型调用集中在此，业务代码不直接 import 模型 SDK。
换模型只需改这里，不影响业务。
"""
import json
import re

from services import ai_settings
from services.access import AccessError


class LLMNotConfiguredError(AccessError):
    """未配置 LLM API Key（HTTP 503，友好提示而非 langchain 抛 500）。"""

    def __init__(self):
        super().__init__(503, "AI 服务未配置 API Key，请在 .env 中设置 DEEPSEEK_API_KEY")


def extract_json(text: str) -> dict:
    """从 LLM 输出中提取 JSON 对象（处理 markdown 代码块与多余文本）。"""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]
    return json.loads(text)


class LLMService:
    def __init__(self, model: str | None = None, api_key: str | None = None):
        cfg = ai_settings.get_text_config()
        self._model = model or cfg["model"]
        self._api_key = api_key or cfg["api_key"]
        self._base_url = cfg["base_url"]
        self._chat = None

    def _get_chat(self):
        if not self._api_key:
            raise LLMNotConfiguredError()
        if self._chat is None:
            from langchain_openai import ChatOpenAI

            self._chat = ChatOpenAI(
                model=self._model,
                api_key=self._api_key,
                base_url=self._base_url,
            )
        return self._chat

    def generate(self, system: str, user: str) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        resp = self._get_chat().invoke(
            [SystemMessage(content=system), HumanMessage(content=user)]
        )
        return resp.content

    def generate_json(self, system: str, user: str) -> dict:
        return extract_json(self.generate(system, user))


def get_llm() -> LLMService:
    return LLMService()
