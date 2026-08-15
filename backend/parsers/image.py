"""图片解析器（多模态视觉 OCR）。

通过 OpenAI 兼容接口调用用户选择的视觉供应商（qwen/openai/gemini/ollama），
把图片中的文字/结构提取为统一的 ParsedDocument，供后续知识提取与 RAG 使用。
"""
import base64
import mimetypes
from pathlib import Path

import httpx

from parsers.base import ParsedDocument, Section
from services import ai_settings

_SYSTEM_PROMPT = (
    "你是一个文档解析助手。请完整识别图片中的文字内容，"
    "保留原有章节层次和阅读顺序，不要翻译，不要总结，不要添加额外解释。"
    "输出纯文本，标题/小节用自然换行表示。"
)


class ImageParser:
    source_type = "image"

    def parse(self, file_path: str) -> ParsedDocument:
        cfg = ai_settings.get_multimodal_config()
        if not cfg["api_key"] and cfg["provider"] != "ollama":
            raise RuntimeError("多模态 API 未配置，请在设置页填写 API Key")

        path = Path(file_path)
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
        data_url = f"data:{mime};base64,{b64}"

        url = f"{cfg['base_url'].rstrip('/')}/chat/completions"
        payload = {
            "model": cfg["model"],
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_url}},
                        {
                            "type": "text",
                            "text": "请识别这张图片中的全部文字内容。",
                        },
                    ],
                },
            ],
            "temperature": 0.1,
        }
        headers = {
            "Authorization": f"Bearer {cfg['api_key']}",
            "Content-Type": "application/json",
        }
        if cfg["provider"] == "ollama":
            headers.pop("Authorization", None)

        try:
            resp = httpx.post(
                url,
                json=payload,
                headers=headers,
                timeout=60,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"多模态接口调用失败：HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"多模态接口调用失败：{exc}") from exc

        data = resp.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("多模态接口返回格式异常") from exc

        if isinstance(content, list):
            content = "".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        if not isinstance(content, str):
            content = str(content)

        paragraphs = [line.strip() for line in content.splitlines() if line.strip()]
        return ParsedDocument(
            title="",
            sections=[Section(title="图片内容", level=1, paragraphs=paragraphs)],
        )
