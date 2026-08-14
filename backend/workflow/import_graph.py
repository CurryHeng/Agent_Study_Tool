"""导入工作流（LangGraph）—— 对齐总体设计 Agent 全家福的 Document / Knowledge Agent。

移植自 agent-quiz-feature/server/src/agent/{graph,document-agent,knowledge-agent}.ts。

  START
    → document_agent   仅当解析无有效章节（sections ≤ 1）时执行：LLM 识别章节结构
    → knowledge_agent  规则预提取 → 短路判断 → 抽样交叉验证 → LLM 决策 → 必要时全量提取
    → validate         普通程序：三层校验
    → 条件边：invalid 且重试 < 2 → knowledge_agent 重试；否则 error
              valid → END

Agent 节点不直接读写数据库/文件系统——缓存经 knowledge_extract_service，
LLM 经 LLMService（可注入 Mock）。与聊天工作流（workflow/graph.py）相互独立。
"""
import json
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from parsers.base import Section
from services import knowledge_extract_service as kes
from services.llm_service import get_llm
from services.structure_extract import (
    build_knowledge_from_structure,
    extract_structure_from_text,
    pick_chunk_size,
    split_text_with_lines,
)

MAX_RETRIES = 2  # 校验失败最多重试 2 次（共 3 次尝试）
MAX_FULL_EXTRACT_CHUNKS = 30  # 全量提取的 LLM 调用上限（同步上传链路，须限制延迟）

CHAPTER_SYSTEM = (
    "你是一个文档结构分析器。给定一段文本，识别其中的章节结构。"
    '输出纯 JSON 对象：{"sections":[{"title":"...","level":1,"paragraphs":["..."]}]}。'
    "level 1 为章、2 为节。段落按原意归入所属章节，不要改写原文。"
    "没有明显章节时输出空 sections 数组。"
)


class ImportState(TypedDict, total=False):
    title: str
    plain_text: str
    sections: list[Section]  # 解析器产出的章节（document_agent 可重建）
    chunks: list  # TextChunk 列表
    knowledge: dict | None
    validation: dict  # {"valid": bool, "errors": [str]}
    retry_count: int
    errors: list[str]
    summary: str


class ImportResult(TypedDict):
    sections: list[Section]
    knowledge: dict | None
    summary: str
    errors: list[str]


def build_import_graph(cache_path=None, llm=None, decision_llm=None):
    """构建导入图。cache_path 为验证缓存文件路径（None 则禁用缓存）。

    llm：知识点提取用 LLM；decision_llm：章节理解/质量决策用 LLM（默认同 llm）。
    """
    extract_llm = llm or get_llm()
    judge_llm = decision_llm or extract_llm

    def _read_cache() -> dict[str, list]:
        return kes.read_validated_cache(cache_path) if cache_path else {}

    def _write_cache(cache: dict[str, list]) -> None:
        if cache_path:
            kes.write_validated_cache(cache_path, cache)

    # ── Document Agent：无章节文档的 LLM 章节理解 ──
    def document_agent(state: ImportState) -> dict:
        try:
            raw = judge_llm.generate_json(
                CHAPTER_SYSTEM, f"文档标题: {state['title']}\n\n{state['plain_text'][:8000]}"
            )
            sections = raw.get("sections") if isinstance(raw, dict) else None
            if not isinstance(sections, list) or not sections:
                return {"summary": "Document Agent: 未识别出明显章节结构，按全文处理"}
            rebuilt = [
                Section(
                    title=str(s.get("title") or f"章节 {i + 1}"),
                    level=min(2, max(1, int(s.get("level") or 1))),
                    paragraphs=[str(p) for p in s.get("paragraphs") or []],
                )
                for i, s in enumerate(sections)
                if isinstance(s, dict)
            ]
            if not rebuilt:
                return {"summary": "Document Agent: 未识别出明显章节结构，按全文处理"}
            return {
                "sections": rebuilt,
                "summary": f"Document Agent: 识别出 {len(rebuilt)} 个章节",
            }
        except Exception as exc:
            return {"errors": [*state.get("errors", []), f"Document Agent 失败: {exc}"]}

    # ── Knowledge Agent：规则 + 抽样交叉验证 + LLM 决策 ──
    def knowledge_agent(state: ImportState) -> dict:
        text = state["plain_text"]
        if not text:
            return {"errors": [*state.get("errors", []), "Knowledge Agent: plain_text 为空"]}
        file_name = state["title"] or "未命名"
        errors = state.get("errors", [])

        # ① 规则预提取
        rule = kes.rule_extract(text, file_name)
        # ② 短路判断：短文档 / 非中英文 / 规则无产出 → 直接全量 LLM
        mode, reason = kes.decide_validation_mode(text, state["chunks"], rule.point_count)
        if mode == "skip":
            reason_map = {
                "short": "文档过短",
                "language": f"非中英文（{rule.language}）",
                "no-rule-points": "规则引擎无产出",
            }
            return _full_extract(
                state, rule.knowledge, file_name, errors,
                f"规则跳过（{reason_map[reason]}），全量提取",
            )

        # ③ 抽样交叉验证
        cache = _read_cache()
        covered = [kp["name"] for kp in kes.get_knowledge_points(rule.knowledge)]
        sample_count = kes.pick_sample_count(len(state["chunks"]))
        indices = kes.uniform_sample(len(state["chunks"]), sample_count)

        all_llm: list[dict] = []
        all_rule: list[dict] = []
        for idx in indices:
            chunk = state["chunks"][idx] if idx < len(state["chunks"]) else None
            if chunk is None:
                continue
            if str(idx) in cache:
                all_llm.extend(cache[str(idx)])
                continue
            # 规则在同一块上重提取
            chunk_structure = extract_structure_from_text(chunk.text)
            chunk_knowledge = build_knowledge_from_structure(chunk_structure, file_name)
            all_rule.extend(kes.get_knowledge_points(chunk_knowledge))
            # LLM 提取同一块
            llm_kps = kes.extract_knowledge_from_chunk(extract_llm, chunk.text, covered)
            cache[str(idx)] = llm_kps
            all_llm.extend(llm_kps)
        _write_cache(cache)

        if not all_llm or not all_rule:
            # 样本无产出（如表格数据），无法对比 → 保守全量
            return _full_extract(
                state, rule.knowledge, file_name, errors, "样本无产出，无法验证，全量提取"
            )

        stats = kes.compute_match_stats(all_llm, all_rule)

        # ④ LLM 决策（失败按硬阈值 fallback）
        try:
            parsed = judge_llm.generate_json(
                kes.DECISION_SYSTEM,
                json.dumps(
                    {
                        "recall": round(stats["recall"], 2),
                        "precision": round(stats["precision"], 2),
                        "matched": stats["matched"],
                        "llmSampleCount": len(all_llm),
                        "ruleSampleCount": len(all_rule),
                        "ruleTotalPoints": rule.point_count,
                        "totalChunks": len(state["chunks"]),
                    },
                    ensure_ascii=False,
                ),
            )
            accept = isinstance(parsed, dict) and parsed.get("accept") is True
            decision_reason = parsed.get("reason", "") if isinstance(parsed, dict) else ""
        except Exception:
            accept = stats["recall"] >= 0.7 and stats["precision"] >= 0.7
            decision_reason = "决策 LLM 失败，按硬阈值"

        if accept:
            return {
                "knowledge": rule.knowledge,
                "summary": (
                    f"交叉验证通过（recall={stats['recall']:.2f}, "
                    f"precision={stats['precision']:.2f}），采纳规则结果"
                ),
            }

        reason_suffix = f"：{decision_reason}" if decision_reason else ""
        return _full_extract(
            state,
            rule.knowledge,
            file_name,
            errors,
            f"交叉验证未通过（recall={stats['recall']:.2f}, "
            f"precision={stats['precision']:.2f}）{reason_suffix}，全量提取",
        )

    # ── 全量提取（复用验证缓存；调用上限 MAX_FULL_EXTRACT_CHUNKS）──
    def _full_extract(
        state: ImportState, rule_knowledge: dict, file_name: str, errors: list[str], prefix: str
    ) -> dict:
        text = state["plain_text"]
        chunks = split_text_with_lines(text, pick_chunk_size(len(text)))
        cache = _read_cache()

        covered = [kp["name"] for kp in kes.get_knowledge_points(rule_knowledge)]
        to_extract = [c.index for c in chunks if str(c.index) not in cache]
        extracted: dict[int, list] = {}
        for idx in to_extract[:MAX_FULL_EXTRACT_CHUNKS]:
            kps = kes.extract_knowledge_from_chunk(extract_llm, chunks[idx].text, covered)
            extracted[idx] = kps
            covered.extend(kp["name"] for kp in kps)

        # 合并：LLM 新提取 + 验证缓存 + 规则兜底（按名称去重）
        all_kps: list[dict] = []
        seen: set[str] = set()

        def push_unique(kps: list[dict]) -> None:
            for kp in kps:
                name = str(kp["name"])
                if name in seen:
                    continue
                seen.add(name)
                all_kps.append(kp)

        for c in chunks:
            cached = cache.get(str(c.index))
            if cached and c.index not in extracted:
                push_unique(cached)
        for kps in extracted.values():
            push_unique(kps)
        # 保留规则结果中 LLM 未覆盖的（规则点可能比 LLM 细）
        push_unique(kes.get_knowledge_points(rule_knowledge))

        knowledge = {
            "title": rule_knowledge.get("title") or file_name,
            "fileName": file_name,
            "chapters": [
                {
                    "chapter_id": "ch_01",
                    "title": rule_knowledge.get("title") or "全文",
                    "content": "",
                    "knowledge_points": [
                        {
                            "id": f"kp_{i + 1:03d}",
                            "name": str(kp["name"]),
                            "importance": min(5, max(1, int(kp.get("importance") or 3))),
                            "difficulty": min(5, max(1, int(kp.get("difficulty") or 2))),
                        }
                        for i, kp in enumerate(all_kps)
                    ],
                }
            ],
        }
        return {
            "knowledge": knowledge,
            "summary": f"{prefix}；LLM 提取 {min(len(to_extract), MAX_FULL_EXTRACT_CHUNKS)} 块，"
            f"合并后 {len(all_kps)} 个知识点",
            "errors": errors,
        }

    # ── 校验（普通程序，三层校验）──
    def validate(state: ImportState) -> dict:
        result = kes.validate_knowledge(state.get("knowledge"))
        retry = state.get("retry_count", 0)
        return {
            "validation": {"valid": result.valid, "errors": result.errors},
            # 失败时递增重试计数（校验发生在 knowledge_agent 之后）
            "retry_count": retry if result.valid else retry + 1,
        }

    def error_node(state: ImportState) -> dict:
        return {"summary": f"导入失败：{'；'.join(state.get('errors', [])) or '未知错误'}"}

    # ── 路由 ──
    def route_after_entry(state: ImportState) -> str:
        # 无有效章节（仅 fallback"全文"或无 sections）→ 需要 Document Agent 理解章节
        return "document_agent" if len(state.get("sections") or []) <= 1 else "knowledge_agent"

    def route_after_validate(state: ImportState) -> str:
        if state.get("validation", {}).get("valid"):
            return END
        if state.get("retry_count", 0) <= MAX_RETRIES:
            return "knowledge_agent"
        return "error"

    graph = StateGraph(ImportState)
    graph.add_node("document_agent", document_agent)
    graph.add_node("knowledge_agent", knowledge_agent)
    graph.add_node("validate", validate)
    graph.add_node("error", error_node)

    graph.add_conditional_edges(
        START,
        route_after_entry,
        {"document_agent": "document_agent", "knowledge_agent": "knowledge_agent"},
    )
    graph.add_edge("document_agent", "knowledge_agent")
    graph.add_edge("knowledge_agent", "validate")
    graph.add_conditional_edges(
        "validate",
        route_after_validate,
        {"knowledge_agent": "knowledge_agent", "error": "error", END: END},
    )
    graph.add_edge("error", END)

    return graph.compile()


def run_import_graph(
    title: str,
    plain_text: str,
    sections: list[Section],
    cache_path=None,
    llm=None,
    decision_llm=None,
) -> ImportResult:
    """执行导入增强：必要时 LLM 章节理解 + 知识点提取（带交叉验证与三层校验）。"""
    graph = build_import_graph(cache_path=cache_path, llm=llm, decision_llm=decision_llm)
    chunks = split_text_with_lines(plain_text, pick_chunk_size(len(plain_text)))
    result = graph.invoke(
        {
            "title": title,
            "plain_text": plain_text,
            "sections": sections,
            "chunks": chunks,
            "knowledge": None,
            "retry_count": 0,
            "errors": [],
            "summary": "",
        }
    )
    return ImportResult(
        sections=result.get("sections") or sections,
        knowledge=result.get("knowledge"),
        summary=result.get("summary", ""),
        errors=result.get("errors", []),
    )


__all__ = ["ImportResult", "ImportState", "build_import_graph", "run_import_graph"]
