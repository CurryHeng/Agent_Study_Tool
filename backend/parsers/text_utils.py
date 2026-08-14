"""纯文本 → 章节的启发式切分（供 PDF 等无结构化标题的文本使用）。

只识别明确的标题特征：第X章/节、数字编号（1.1）、中文数字编号（一、）。
标题保留完整原文（含编号），正文行归入最近的章节。
"""
import re

from parsers.base import ParsedDocument, Section

_CHAPTER_RE = re.compile(r"^第[一二三四五六七八九十百零\d]+[章节篇]")
_NUMBERED_RE = re.compile(r"^(\d+(?:\.\d+)*)[、.\s]")
_CN_NUMBERED_RE = re.compile(r"^[一二三四五六七八九十]+[、.]")


def split_text_to_sections(text: str, source_type: str) -> ParsedDocument:
    sections: list[Section] = []
    current: Section | None = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        level = 1
        if _CHAPTER_RE.match(line):
            level = 1
        elif _NUMBERED_RE.match(line):
            level = _NUMBERED_RE.match(line).group(1).count(".") + 1
        elif _CN_NUMBERED_RE.match(line):
            level = 1
        else:
            if current is not None:
                current.paragraphs.append(line)
            continue

        current = Section(title=line, level=level)
        sections.append(current)

    return ParsedDocument(title="", source_type=source_type, sections=sections)
