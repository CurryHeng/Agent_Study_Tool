"""解析器注册表与统一入口。"""
from pathlib import Path

from parsers.base import ParsedDocument
from parsers.html import HtmlParser
from parsers.image import ImageParser
from parsers.markdown import MarkdownParser
from parsers.pdf import PdfParser
from parsers.ppt import PptParser
from parsers.word import WordParser

PARSERS = {
    "markdown": MarkdownParser,
    "pdf": PdfParser,
    "word": WordParser,
    "ppt": PptParser,
    "image": ImageParser,
    "html": HtmlParser,
}

EXT_MAP = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".txt": "markdown",
    ".pdf": "pdf",
    ".docx": "word",
    ".pptx": "ppt",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".html": "html",
    ".htm": "html",
}


def detect_type(filename: str) -> str | None:
    ext = Path(filename).suffix.lower()
    return EXT_MAP.get(ext)


def parse_file(file_path: str, file_type: str) -> ParsedDocument:
    """统一解析入口：解析文件并用文件名补齐标题。"""
    parser = PARSERS[file_type]()
    parsed = parser.parse(file_path)
    if not parsed.title:
        parsed.title = Path(file_path).stem
    parsed.source_type = file_type
    return parsed
