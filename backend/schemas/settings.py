"""AI 供应商设置 Pydantic 模型。"""
from pydantic import BaseModel


class ProviderConfig(BaseModel):
    provider: str
    api_key: str = ""
    model: str = ""


class AiSettingsIn(BaseModel):
    text: ProviderConfig
    multimodal: ProviderConfig


class AiSettingsOut(BaseModel):
    text: ProviderConfig
    multimodal: ProviderConfig
