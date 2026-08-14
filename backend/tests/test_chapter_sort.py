"""中文章节排序测试（引用真实源码 services/chapter_sort.py）。"""
from services.chapter_sort import parse_chapter_number, sort_chapters


def test_parse_simple():
    assert parse_chapter_number("第一章 函数极限") == 1
    assert parse_chapter_number("第二章 导数") == 2
    assert parse_chapter_number("第十章 反常积分") == 10


def test_parse_compound_11_20():
    assert parse_chapter_number("第十一章") == 11
    assert parse_chapter_number("第十五章") == 15
    assert parse_chapter_number("第二十章") == 20


def test_parse_21_99():
    assert parse_chapter_number("第二十一章") == 21
    assert parse_chapter_number("第三十五章") == 35
    assert parse_chapter_number("第九十九章") == 99


def test_parse_tens():
    assert parse_chapter_number("第三十章") == 30
    assert parse_chapter_number("第四十章") == 40


def test_parse_unknown():
    assert parse_chapter_number("附录") == 999
    assert parse_chapter_number("") == 999


def test_sort_chapters():
    assert sort_chapters(["第三章", "第一章", "第十章", "第二章"]) == [
        "第一章", "第二章", "第三章", "第十章",
    ]


def test_sort_mixed_digits():
    assert sort_chapters(["第十一章", "第一章", "第二十章", "第二章"]) == [
        "第一章", "第二章", "第十一章", "第二十章",
    ]


def test_sort_unknown_last():
    result = sort_chapters(["AI 生成", "第一章", "附录", "第二章"])
    assert result[0] == "第一章"
    assert result[1] == "第二章"
    assert "AI 生成" in result[2:]
    assert "附录" in result[2:]
