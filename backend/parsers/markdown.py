"""Markdown / 纯文本解析器（按 # 标题层级切分）。"""
import re
from pathlib import Path

from parsers.base import BaseParser, ParsedDocument, Section

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)")


class MarkdownParser(BaseParser):
    source_type = "markdown"

    def parse(self, file_path: str) -> ParsedDocument:
        text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        sections: list[Section] = []
        current: Section | None = None

        for line in text.splitlines():
            m = _HEADING_RE.match(line)
            if m:
                level = len(m.group(1))
                title = m.group(2).strip()
                current = Section(title=title, level=level)
                sections.append(current)
            elif current is not None and line.strip():
                current.paragraphs.append(line.strip())

        return ParsedDocument(title="", source_type=self.source_type, sections=sections)
