"""图片解析器（占位）。

图片内容解析依赖千问视觉模型，属于后续阶段；这里保留统一接口，
`parse` 直接抛出 NotImplementedError，由上层给出明确提示。
"""
from parsers.base import ParsedDocument


class ImageParser:
    source_type = "image"

    def parse(self, file_path: str) -> ParsedDocument:
        raise NotImplementedError("图片解析（视觉 Agent）将在后续阶段实现")
