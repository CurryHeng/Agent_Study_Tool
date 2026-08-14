"""中文章节号解析与排序（Python 移植）。

来源：旧项目 `src/lib/storage.ts` / `src/lib/schema.ts` 的 parseChapterNumber。
"""
CN_NUM: dict[str, int] = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}
CN_NUM_REV: dict[str, int] = {
    "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15,
    "十六": 16, "十七": 17, "十八": 18, "十九": 19, "二十": 20,
}


def parse_chapter_number(chapter: str) -> int:
    """解析 '第X章' 为整数，无法识别返回 999（排到最后）。"""
    import re

    m = re.match(r"^第(.+?)章", chapter)
    if not m:
        return 999
    cn = m[1]
    if cn in CN_NUM_REV:
        return CN_NUM_REV[cn]
    if cn.startswith("十"):
        return 10 + (CN_NUM.get(cn[1], 0) if len(cn) > 1 else 0)
    if cn.endswith("十"):
        return CN_NUM.get(cn[0], 0) * 10
    if len(cn) == 3 and CN_NUM.get(cn[0]) and CN_NUM.get(cn[2]):
        return CN_NUM[cn[0]] * 10 + CN_NUM[cn[2]]
    if len(cn) == 1:
        return CN_NUM.get(cn, 999)
    return 999


def sort_chapters(chapters: list[str]) -> list[str]:
    """按中文数字顺序排序章节名。"""
    return sorted(chapters, key=parse_chapter_number)
