"""思维导图（知识树）构建。"""
import re

from sqlalchemy.orm import Session

from models import Workbook
from repositories import knowledge_repository
from schemas.mindmap import MindMapNode, MindMapOut

_ROMAN_VALUES = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}


def _roman_to_int(roman: str) -> int:
    """罗马数字→int（I~MMM）。"""
    total = 0
    prev = 0
    for ch in reversed(roman.lower()):
        val = _ROMAN_VALUES.get(ch, 0)
        if val < prev:
            total -= val
        else:
            total += val
            prev = val
    return total


def _sort_key(name: str) -> tuple:
    """排序键：按名称开头的章节编号排序，无编号排最后。

    支持（多语言）：
    - 数字编号：'1.2 xxx'、'1. Introduction'
    - 中文：'第3章 xxx'、'三、xxx'
    - 英文/外语：'Chapter 2'、'Chapter IV'、'Section 3.1'、
      'Part A'、'Part II'、'Unit 4'、'Lesson 5'、'Module 2'
    """
    text = (name or "").strip()
    m = re.match(r"^(\d+(?:\.\d+)*)", text)
    if m:
        parts = [int(p) for p in m.group(1).split(".")]
        return (0, parts, text)
    m = re.match(r"^第([一二三四五六七八九十百\d]+)[章节篇]", text)
    if m:
        return (1, [_cn_to_int(m.group(1))], text)
    m = re.match(r"^([一二三四五六七八九十]+)[、.．]", text)
    if m:
        return (1, [_cn_to_int(m.group(1))], text)
    # 英文/外语：Chapter 2 / Chapter IV / Section 3.1
    m = re.match(r"^(?:chapter|section)\s+(\d+|[ivxlcdm]+)", text, re.IGNORECASE)
    if m:
        num = _roman_to_int(m.group(1)) if m.group(1).isalpha() else int(m.group(1))
        return (0, [num], text)
    # Part A / Part II / Unit 4 / Lesson 5 / Module 2
    m = re.match(r"^(?:part|unit|lesson|module)\s+(\d+|[a-z]+|[ivxlcdm]+)", text, re.IGNORECASE)
    if m:
        token = m.group(1)
        if token.isdigit():
            num: tuple = (int(token),)
        elif re.fullmatch(r"[ivxlcdm]+", token, re.IGNORECASE):
            num = (_roman_to_int(token),)
        else:
            num = (ord(token[0].upper()),)  # 字母序：Part A < Part B
        return (1, num, text)
    return (2, [], text)


def _cn_to_int(cn: str) -> int:
    """中文数字→int（支持 一~九十九、百）。"""
    digits = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if cn.isdigit():
        return int(cn)
    total = 0
    if "百" in cn:
        head, _, tail = cn.partition("百")
        total += digits.get(head, 0) * 100
        cn = tail
    if "十" in cn:
        head, _, tail = cn.partition("十")
        total += digits.get(head, 1) * 10
        cn = tail
    total += digits.get(cn, 0)
    return total


def build_mindmap(db: Session, workbook: Workbook) -> MindMapOut:
    """把工作簿下的 Knowledge 节点组装成树（根节点 = 工作簿名，按章节号排序）。"""
    nodes = knowledge_repository.list_by_workbook(db, workbook.id)
    node_map = {n.id: MindMapNode(id=n.id, label=n.name, children=[]) for n in nodes}
    roots: list[MindMapNode] = []

    for n in nodes:
        if n.parent_id is not None and n.parent_id in node_map:
            node_map[n.parent_id].children.append(node_map[n.id])
        else:
            roots.append(node_map[n.id])

    def sort_rec(node: MindMapNode) -> None:
        node.children.sort(key=lambda c: _sort_key(c.label))
        for c in node.children:
            sort_rec(c)

    for r in roots:
        sort_rec(r)
    roots.sort(key=lambda n: _sort_key(n.label))

    root = MindMapNode(id=workbook.id, label=workbook.name, children=roots)
    return MindMapOut(root=root)


def to_markmap(node: MindMapNode) -> dict:
    """转换为 markmap 渲染所需格式（content + children）。"""
    return {"content": node.label, "children": [to_markmap(c) for c in node.children]}
