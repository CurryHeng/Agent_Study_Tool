"""PPT（.pptx）解析器，每页幻灯片作为一个知识点。"""
from pptx import Presentation

from parsers.base import ParsedDocument, Section


class PptParser:
    source_type = "ppt"

    def parse(self, file_path: str) -> ParsedDocument:
        prs = Presentation(file_path)
        sections: list[Section] = []

        for index, slide in enumerate(prs.slides, start=1):
            title = slide.shapes.title.text.strip() if slide.shapes.title else f"第 {index} 页"
            paragraphs: list[str] = []
            for shape in slide.shapes:
                if shape is slide.shapes.title or not shape.has_text_frame:
                    continue
                for p in shape.text_frame.paragraphs:
                    text = "".join(run.text for run in p.runs).strip()
                    if text:
                        paragraphs.append(text)
            sections.append(
                Section(title=title or f"第 {index} 页", level=1, paragraphs=paragraphs)
            )

        return ParsedDocument(title="", source_type=self.source_type, sections=sections)
