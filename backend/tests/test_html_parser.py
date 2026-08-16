"""HTML 解析器测试。"""
from pathlib import Path

from parsers.factory import detect_type, parse_file


def _write_html(tmp_path: Path) -> str:
    p = tmp_path / "sample.html"
    p.write_text(
        "<html><body>"
        "<h1>第一章 函数</h1>"
        "<p>函数定义</p>"
        "<h2>1.1 极限</h2>"
        "<p>极限定义</p>"
        "</body></html>",
        encoding="utf-8",
    )
    return str(p)


def test_detect_html_type(tmp_path):
    assert detect_type("a.html") == "html"
    assert detect_type("a.htm") == "html"


def test_html_parser_extracts_sections(tmp_path):
    parsed = parse_file(_write_html(tmp_path), "html")
    assert parsed.title == "sample"
    assert len(parsed.sections) >= 2
    assert parsed.sections[0].title == "第一章 函数"
    assert any("极限" in s.title for s in parsed.sections)
