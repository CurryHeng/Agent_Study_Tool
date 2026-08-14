"""应用配置（pydantic-settings，统一从 .env 读取）。

所有密钥/模型参数/路径一律走这里，代码中禁止硬编码。
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── 数据库 ──
    database_url: str = f"sqlite:///{(DATA_DIR / 'quiz-app.db').as_posix()}"

    # ── 认证（P0-2 使用）──
    jwt_secret: str = "dev-only-change-me-in-production-0123456789abcdef"
    encryption_key: str = ""

    # ── LLM（后续阶段使用）──
    deepseek_api_key: str = ""
    qwen_api_key: str = ""
    llm_model: str = "deepseek-chat"
    embedding_model: str = "chroma-default"  # chroma-default = 本地 ONNX MiniLM（免 key）

    # ── RAG ──
    chroma_path: str = str(DATA_DIR / "chroma")
    chunk_size: int = 500

    # ── 文件（后续阶段使用）──
    max_file_size: int = 10 * 1024 * 1024  # 10 MB
    max_retry: int = 2
    upload_dir: str = str(DATA_DIR / "uploads")


settings = Settings()
