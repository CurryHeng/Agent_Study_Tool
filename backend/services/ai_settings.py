"""AI 供应商配置（文本 LLM + 多模态视觉）。

配置保存在 backend/data/ai_settings.json（不入库、不入 git），
未保存时回退到 .env 中的 DEEPSEEK_API_KEY / QWEN_API_KEY。
"""
import json
from pathlib import Path

from config import DATA_DIR, settings

_SETTINGS_PATH = Path(DATA_DIR) / "ai_settings.json"

# 常见供应商的 OpenAI 兼容 endpoint 与默认模型
PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-1.5-flash",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.2",
    },
}

TEXT_PROVIDERS = ["deepseek", "openai", "qwen", "gemini", "ollama"]
MULTIMODAL_PROVIDERS = ["qwen", "openai", "gemini", "ollama"]


def _load() -> dict:
    if not _SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict) -> None:
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _resolve(kind: str) -> dict:
    """返回 {provider, api_key, model, base_url}，带 .env 回退。"""
    saved = _load().get(kind, {})
    if kind == "text":
        default_provider = "deepseek"
        env_key = settings.deepseek_api_key
        env_model = settings.llm_model
    else:
        default_provider = "qwen"
        env_key = settings.qwen_api_key
        env_model = settings.qwen_vl_model

    provider = saved.get("provider") or default_provider
    if provider not in PROVIDER_PRESETS:
        provider = default_provider
    preset = PROVIDER_PRESETS[provider]
    return {
        "provider": provider,
        "api_key": saved.get("api_key") or env_key or "",
        "model": saved.get("model") or env_model or preset["model"],
        "base_url": preset["base_url"],
    }


def get_text_config() -> dict:
    return _resolve("text")


def get_multimodal_config() -> dict:
    return _resolve("multimodal")


def get_ai_settings() -> dict:
    return {
        "text": get_text_config(),
        "multimodal": get_multimodal_config(),
    }


def save_ai_settings(payload: dict) -> dict:
    text = payload.get("text") or {}
    multimodal = payload.get("multimodal") or {}

    text_provider = text.get("provider") or "deepseek"
    multimodal_provider = multimodal.get("provider") or "qwen"
    if text_provider not in TEXT_PROVIDERS:
        raise ValueError(f"不支持的文本供应商：{text_provider}")
    if multimodal_provider not in MULTIMODAL_PROVIDERS:
        raise ValueError(f"不支持的多模态供应商：{multimodal_provider}")

    data = {
        "text": {
            "provider": text_provider,
            "api_key": (text.get("api_key") or "").strip(),
            "model": (text.get("model") or "").strip(),
        },
        "multimodal": {
            "provider": multimodal_provider,
            "api_key": (multimodal.get("api_key") or "").strip(),
            "model": (multimodal.get("model") or "").strip(),
        },
    }
    _save(data)
    return get_ai_settings()
