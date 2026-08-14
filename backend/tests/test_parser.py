"""文档解析器测试（markdown / word / ppt + 类型识别）。"""
from parsers.factory import detect_type, parse_file


def test_detect_type():
    assert detect_type("a.md") == "markdown"
    assert detect_type("a.markdown") == "markdown"
    assert detect_type("a.txt") == "markdown"
    assert detect_type("a.pdf") == "pdf"
    assert detect_type("a.docx") == "word"
    assert detect_type("a.pptx") == "ppt"
    assert detect_type("a.png") == "image"
    assert detect_type("a.xyz") is None


def test_markdown_parser(tmp_path):
    md = "# 第一章\n\n内容1\n\n## 知识点A\n\n内容2\n"
    path = tmp_path / "outline.md"
    path.write_text(md, encoding="utf-8")

    parsed = parse_file(str(path), "markdown")
    assert parsed.title == "outline"
    assert len(parsed.sections) == 2
    assert parsed.sections[0].title == "第一章"
    assert parsed.sections[0].level == 1
    assert "内容1" in parsed.sections[0].paragraphs
    assert parsed.sections[1].title == "知识点A"
    assert parsed.sections[1].level == 2


def test_word_parser(tmp_path):
    from docx import Document as Docx

    doc = Docx()
    doc.add_heading("第一章", level=1)
    doc.add_paragraph("段落1")
    doc.add_heading("知识点A", level=2)
    doc.add_paragraph("段落2")
    path = tmp_path / "outline.docx"
    doc.save(str(path))

    parsed = parse_file(str(path), "word")
    titles = [s.title for s in parsed.sections]
    assert "第一章" in titles
    assert "知识点A" in titles


def test_ppt_parser(tmp_path):
    from pptx import Presentation

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "知识点A"
    path = tmp_path / "outline.pptx"
    prs.save(str(path))

    parsed = parse_file(str(path), "ppt")
    assert len(parsed.sections) == 1
    assert parsed.sections[0].title == "知识点A"


def test_text_utils_split():
    from parsers.text_utils import split_text_to_sections

    text = "第一章 函数与极限\n函数的定义\n1.1 极限\n极限的定义\n第二章 导数\n"
    parsed = split_text_to_sections(text, "pdf")
    titles = [s.title for s in parsed.sections]
    assert "第一章 函数与极限" in titles
    assert "1.1 极限" in titles
    assert "第二章 导数" in titles
