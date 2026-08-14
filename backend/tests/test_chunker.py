"""文档切块测试。"""
from rag.chunker import chunk_document


class _S:
    def __init__(self, title, level, paragraphs):
        self.title = title
        self.level = level
        self.paragraphs = paragraphs


def test_chunk_basic():
    sections = [_S("第一章", 1, ["内容1"]), _S("知识点A", 2, ["内容2"])]
    chunks = chunk_document(sections, [11, 22], document_id=1)
    assert len(chunks) == 2
    assert chunks[0].chunk_id == "d1-s0-c0"
    assert chunks[0].knowledge_id == 11
    assert chunks[0].content.startswith("第一章")
    assert chunks[1].chunk_id == "d1-s1-c0"
    assert chunks[1].knowledge_id == 22


def test_chunk_content_includes_paragraphs():
    sections = [_S("第一章", 1, ["para1", "para2"])]
    chunks = chunk_document(sections, [1], document_id=1)
    assert len(chunks) == 1
    assert "para1" in chunks[0].content
    assert "para2" in chunks[0].content


def test_chunk_split_long():
    sections = [_S("长章", 1, ["x" * 1200])]
    chunks = chunk_document(sections, [1], document_id=1, chunk_size=500)
    assert len(chunks) == 3
    assert all(c.chunk_id.startswith("d1-s0-c") for c in chunks)
    assert all(c.knowledge_id == 1 for c in chunks)


def test_chunk_skips_empty_section():
    sections = [_S("", 1, [])]
    chunks = chunk_document(sections, [1], document_id=1)
    assert chunks == []
