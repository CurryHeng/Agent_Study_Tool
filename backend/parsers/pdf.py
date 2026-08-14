"""PDF 解析器（pypdf 提取文本 + 启发式章节切分）。"""
from pypdf import PdfReader

from parsers.base import ParsedDocument
from parsers.text_utils import split_text_to_sections


class PdfParser:
    source_type = "pdf"

    def parse(self, file_path: str) -> ParsedDocument:
        reader = PdfReader(file_path)
        parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        return split_text_to_sections("\n".join(parts), self.source_type)
