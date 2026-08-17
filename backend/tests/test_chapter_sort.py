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


# ── 思维导图多语言排序（mindmap_service._sort_key） ──


def test_sort_key_roman_numerals():
    """罗马数字章节正确排序：Chapter IV 在 Chapter X 前。"""
    from services.mindmap_service import _sort_key

    names = ["Chapter X", "Chapter IV", "Chapter II", "Chapter VIII"]
    assert sorted(names, key=_sort_key) == [
        "Chapter II", "Chapter IV", "Chapter VIII", "Chapter X",
    ]


def test_sort_key_part_and_unit():
    """外语教材分层：Part A < Part B；Unit 2 < Unit 10（数字序而非字典序）。"""
    from services.mindmap_service import _sort_key

    parts = sorted(["Part B", "Part A"], key=_sort_key)
    assert parts == ["Part A", "Part B"]
    units = sorted(["Unit 10", "Unit 2", "Unit 5"], key=_sort_key)
    assert units == ["Unit 2", "Unit 5", "Unit 10"]


def test_sort_key_mixed_languages():
    """混合语言文档：数字编号与 Chapter 同层有序，无编号排最后。"""
    from services.mindmap_service import _sort_key

    names = ["附录", "Chapter 1", "2. Methods", "Chapter 3", "1. Introduction"]
    result = sorted(names, key=_sort_key)
    # 数字编号与 Chapter 同层有序（按编号），无编号的"附录"排最后
    assert result.index("1. Introduction") < result.index("2. Methods")
    assert result.index("2. Methods") < result.index("Chapter 3")
    assert result[-1] == "附录"
