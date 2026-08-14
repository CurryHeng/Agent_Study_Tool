"""文档解析统一数据结构与基类。

设计原则（详细设计 Pt.1 §9/§10）：
- 所有解析器统一接口 `parse(file_path) -> ParsedDocument`。
- 文件解析属于普通程序能力（确定性），与 Agent 内容理解解耦。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Section:
    """文档的一个章节/段落块。"""

    title: str
    level: int
    paragraphs: list[str] = field(default_factory=list)


@dataclass
class ParsedDocument:
    """统一的文档中间表示。"""

    title: str = ""
    source_type: str = ""
    sections: list[Section] = field(default_factory=list)


class BaseParser(ABC):
    """解析器基类。"""

    source_type: str = ""

    @abstractmethod
    def parse(self, file_path: str) -> ParsedDocument:
        raise NotImplementedError
