"""HTML 解析器（基础版）：识别标题与正文，输出统一 Document Representation。"""
from html.parser import HTMLParser

from parsers.base import ParsedDocument, Section

_HEADING_LEVELS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
_TEXT_TAGS = {"p", "li", "td", "th", "div", "span", "dt", "dd", "pre", "blockquote"}


class _HtmlToSections(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sections: list[Section] = []
        self.current: Section | None = None
        self._buffer: list[str] = []
        self._in_heading = False
        self._heading_level = 0
        self._in_text = False

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _HEADING_LEVELS:
            self._flush_text()
            self._in_heading = True
            self._heading_level = _HEADING_LEVELS[tag]
            self._buffer = []
        elif tag in _TEXT_TAGS:
            self._in_text = True

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _HEADING_LEVELS:
            text = " ".join("".join(self._buffer).split())
            self._buffer = []
            if text:
                self.sections.append(Section(title=text, level=self._heading_level))
                self.current = self.sections[-1]
            self._in_heading = False
            self._heading_level = 0
        elif tag in _TEXT_TAGS:
            self._in_text = False
            self._flush_text()

    def handle_data(self, data):
        if self._in_heading or self._in_text:
            self._buffer.append(data)

    def _flush_text(self):
        text = " ".join("".join(self._buffer).split())
        self._buffer = []
        if not text:
            return
        if self.current is None:
            self.sections.append(Section(title="内容", level=1, paragraphs=[text]))
        else:
            self.current.paragraphs.append(text)


class HtmlParser:
    source_type = "html"

    def parse(self, file_path: str) -> ParsedDocument:
        content = open(file_path, encoding="utf-8", errors="ignore").read()
        parser = _HtmlToSections()
        parser.feed(content)
        return ParsedDocument(title="", sections=parser.sections)
