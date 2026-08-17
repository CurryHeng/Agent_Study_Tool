"""纯文本 → 章节的启发式切分（供 PDF 等无结构化标题的文本使用）。

只识别明确的标题特征：第X章/节、数字编号（1.1）、中文数字编号（一、）。
标题保留完整原文（含编号），正文行归入最近的章节。
垃圾行（公式乱码/泛标题/参考文献条目）不认作章节——复用知识名字清洗，
与知识点提取同一过滤标准。
"""
import re

from parsers.base import ParsedDocument, Section

_CHAPTER_RE = re.compile(r"^第[一二三四五六七八九十百零\d]+[章节篇]")
_NUMBERED_RE = re.compile(r"^(\d+(?:\.\d+)*)[、.\s]")
_CN_NUMBERED_RE = re.compile(r"^[一二三四五六七八九十]+[、.]")


# ── 知识点/章节名清洗（供 Parser 与 Service 共用，避免 Parser 依赖 Service） ──
_TERM_CLEAN_RE = re.compile(r"[，。、；：,.;:]+\s*$")

# PDF 文本层常见的数学编码残留字符（pypdf 提取公式时常出现）
_PDF_GARBLE_RE = re.compile(r"[/\\]C[0-9]|[ðþ¼¾]|¼|™|K")
# 泛标题：编号可选的章节泛称（"1 Introduction"/"参考文献"/"Chapter 2" 这类不带具体主题的标题）
_GENERIC_HEADING_RE = re.compile(
    r"^(?:\d+(?:\.\d+)*|[一二三四五六七八九十]+|chapter\s*\d+|section\s*\d+)?"
    r"[\s、.．]*(?:"
    r"introduction|chapter|section|conclusion|conclusions|appendix|references|"
    r"abstract|overview|summary|contents|前言|绪论|引言|总结|结论|参考文献|附录|目录)$",
    re.IGNORECASE,
)
# 参考文献条目：Author - Year - Title / [n] Author, "Title", Year
_REF_ENTRY_RE = re.compile(
    r"^(?:\[\d+\]\s*)?(?:[A-Z][\w'\-]+\s+){1,4}(?:等\s*)?[-–—]?\s*\d{4}[a-z]?\s*[-–—.,:]",
)
# 纯数字/符号（公式行碎片）
_NUM_SYMBOL_RE = re.compile(r"^[\d\s.,;:()\[\]{}<>=+\-*/^_~|\\]+$")


def _clean_kp_name(name: str) -> str | None:
    """清洗知识点名字；返回 None 表示应丢弃。

    过滤：PDF 公式乱码、纯编号泛标题、参考文献条目、纯数字符号行；
    截断：超过 40 字符的整句，在最后一个空格/逗号处断开取短语。
    """
    name = name.strip()
    name = name[2:-2] if name.startswith("**") and name.endswith("**") else name
    name = name.strip()
    if not name or len(name) < 2:
        return None
    if _PDF_GARBLE_RE.search(name):
        return None
    if _GENERIC_HEADING_RE.match(name):
        return None
    if _REF_ENTRY_RE.match(name):
        return None
    if _NUM_SYMBOL_RE.match(name):
        return None
    if len(name) > 40:
        cut = max(name.rfind(" ", 0, 40), name.rfind(",", 0, 40), name.rfind("，", 0, 40))
        name = name[:cut] if cut >= 8 else name[:40]
        name = name.rstrip("，,。.：:；; ")
    name = _TERM_CLEAN_RE.sub("", name).strip()
    if len(name) < 2:
        return None
    return name


def split_text_to_sections(text: str, source_type: str) -> ParsedDocument:
    sections: list[Section] = []
    current: Section | None = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        level: int | None = None
        if _CHAPTER_RE.match(line):
            level = 1
        elif _NUMBERED_RE.match(line):
            level = _NUMBERED_RE.match(line).group(1).count(".") + 1
        elif _CN_NUMBERED_RE.match(line):
            level = 1

        if level is None:
            if current is not None:
                current.paragraphs.append(line)
            continue

        # 候选标题过清洗：公式乱码/泛标题/参考文献不认作章节，作为正文归入上一章节
        clean = _clean_kp_name(line)
        if clean is None:
            if current is not None:
                current.paragraphs.append(line)
            continue

        current = Section(title=clean, level=level)
        sections.append(current)

    return ParsedDocument(title="", source_type=source_type, sections=sections)
