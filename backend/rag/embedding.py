"""Embedding 抽象与工厂。

模型通过配置注入（settings.embedding_model），不硬编码：
- chroma-default：本地 ONNX all-MiniLM-L6-v2（免 API key，Chroma 默认）
- 未来可扩展 sentence-transformers / dashscope 等
"""
from abc import ABC, abstractmethod

from config import settings


class BaseEmbedder(ABC):
    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError


class ChromaEmbedder(BaseEmbedder):
    """Chroma 默认本地 ONNX 嵌入（首次调用会下载模型）。"""

    def __init__(self):
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

        self._fn = DefaultEmbeddingFunction()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._fn(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._fn([text])[0]


def get_embedder() -> BaseEmbedder:
    model = settings.embedding_model
    if model in ("", "chroma-default"):
        return ChromaEmbedder()
    raise ValueError(f"未知的 embedding 模型：{model}")
