"""文档切块。

策略（详细设计 Pt.2 §4.2）：章节 → 段落 → 固定长度 chunk，优先不破坏语义。
P0-5 以「每个章节为一个 chunk」，超长时按固定大小切分。
"""
from dataclasses import dataclass


@dataclass
class Chunk:
    chunk_id: str
    content: str
    section: str
    knowledge_id: int | None = None


def _split(text: str, max_size: int) -> list[str]:
    if len(text) <= max_size:
        return [text]
    return [text[i : i + max_size] for i in range(0, len(text), max_size)]


def chunk_document(
    sections: list,
    section_knowledge: list[int | None],
    document_id: int,
    chunk_size: int = 500,
) -> list[Chunk]:
    """把解析出的章节切成 chunk。

    sections 元素需具备 `.title` / `.level` / `.paragraphs` 属性。
    section_knowledge[i] 对应 sections[i] 的知识点 id（可 None）。
    """
    chunks: list[Chunk] = []
    for i, section in enumerate(sections):
        knowledge_id = section_knowledge[i] if i < len(section_knowledge) else None
        content = (section.title + "\n" + "\n".join(section.paragraphs)).strip()
        if not content:
            continue
        for j, piece in enumerate(_split(content, chunk_size)):
            chunks.append(
                Chunk(
                    chunk_id=f"d{document_id}-s{i}-c{j}",
                    content=piece,
                    section=section.title,
                    knowledge_id=knowledge_id,
                )
            )
    return chunks
