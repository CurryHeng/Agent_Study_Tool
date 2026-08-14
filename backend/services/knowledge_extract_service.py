"""知识提取服务：规则预提取 + 抽样交叉验证 + 三层校验 + 验证缓存。

移植自 agent-quiz-feature/server/src/services/knowledge-service.ts 与 llm-service.ts。
确定性逻辑（规则/抽样/统计/校验/缓存）为普通程序；仅 extract_knowledge_from_chunk
与决策调用走 LLM（经 LLMService，可注入 Mock）。
"""
import json
import re
from dataclasses import dataclass
from pathlib import Path

from services.structure_extract import (
    StructureResult,
    TextChunk,
    build_knowledge_from_structure,
    compute_match_stats,
    detect_language,
    extract_structure_from_text,
)

EXTRACT_SYSTEM = (
    "你是一个知识提取器。从给定文本中提取知识点（术语/概念）。"
    "输出纯 JSON 数组（不要 Markdown 包裹），每个元素："
    '{"name":"...","importance":3,"difficulty":2}。'
    "importance 和 difficulty 都是 1-5 整数。只提取有实质意义的概念，跳过过渡句和通用词。"
)

DECISION_SYSTEM = (
    "你是知识提取质量决策器。给定规则引擎与 LLM 抽样对比的指标，决定是否信任规则结果。"
    '输出纯 JSON：{"accept":true} 或 {"accept":false,"reason":"..."}。'
    "recall 是规则漏提率（1-recall 为漏提），precision 是规则误提率（1-precision 为误提）。"
    "默认标准：recall ≥ 0.7 且 precision ≥ 0.7 则接受；0.6-0.7 边缘时，"
    "若漏提的多为示例/过渡性内容可接受。经济性优先：能用规则结果就不做全量提取。"
)


# ── 规则预提取 ─────────────────────────────────────────────────────────


@dataclass
class RuleExtraction:
    knowledge: dict
    structure: StructureResult
    language: str
    point_count: int


def get_knowledge_points(knowledge: dict) -> list[dict]:
    chapters = (knowledge or {}).get("chapters")
    if not isinstance(chapters, list):
        return []
    return [kp for ch in chapters for kp in ch.get("knowledge_points", [])]


def rule_extract(text: str, file_name: str) -> RuleExtraction:
    structure = extract_structure_from_text(text)
    knowledge = build_knowledge_from_structure(structure, file_name)
    return RuleExtraction(
        knowledge=knowledge,
        structure=structure,
        language=structure.language,
        point_count=len(get_knowledge_points(knowledge)),
    )


# ── 抽样 ───────────────────────────────────────────────────────────────


def uniform_sample(total: int, n: int) -> list[int]:
    if n >= total:
        return list(range(total))
    indices = {0, total - 1}
    step = (total - 1) / (n - 1)
    for k in range(1, n - 1):
        indices.add(round(k * step))
    return sorted(indices)


def pick_sample_count(chunk_count: int) -> int:
    if chunk_count <= 5:
        return 0
    return min(8, max(3, -(-chunk_count * 15 // 100)))  # ceil(0.15 * n)


# ── 短路判断 ───────────────────────────────────────────────────────────


def decide_validation_mode(text: str, chunks: list[TextChunk], rule_points: int) -> tuple[str, str]:
    """返回 (mode, reason)：mode = "skip"（直接全量 LLM）| "validate"（先交叉验证）。"""
    if len(chunks) <= 5:
        return "skip", "short"
    lang = detect_language(text)
    if lang not in ("zh", "en"):
        return "skip", "language"
    if rule_points == 0:
        return "skip", "no-rule-points"
    return "validate", ""


# ── 三层校验 ───────────────────────────────────────────────────────────


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]


def validate_knowledge(knowledge) -> ValidationResult:
    errors: list[str] = []

    # ① 格式校验：是对象且不是字符串/错误响应
    if not isinstance(knowledge, dict):
        return ValidationResult(False, ["格式错误：不是合法对象"])
    if knowledge.get("error"):
        return ValidationResult(False, [str(knowledge["error"])])

    # ② 结构校验：必需字段
    if not isinstance(knowledge.get("chapters"), list):
        return ValidationResult(False, ["结构错误：缺少 chapters 数组"])

    # ③ 业务校验：每章/每个知识点字段合法
    for ch in knowledge["chapters"]:
        if not isinstance(ch, dict):
            errors.append("业务错误：存在非法章节")
            continue
        if not ch.get("title") or not isinstance(ch.get("knowledge_points"), list):
            title = ch.get("title") or "?"
            errors.append(f"业务错误：章节 \"{title}\" 缺少 title 或 knowledge_points")
            continue
        for kp in ch["knowledge_points"]:
            if not isinstance(kp, dict) or not kp.get("name"):
                errors.append(f"业务错误：章节 \"{ch['title']}\" 存在无 name 的知识点")
                continue
            imp, diff = kp.get("importance"), kp.get("difficulty")
            if imp is not None and not (isinstance(imp, int | float) and 1 <= imp <= 5):
                errors.append(f"业务错误：知识点 \"{kp['name']}\" importance 超出 1-5")
            if diff is not None and not (isinstance(diff, int | float) and 1 <= diff <= 5):
                errors.append(f"业务错误：知识点 \"{kp['name']}\" difficulty 超出 1-5")

    return ValidationResult(not errors, errors)


# ── 验证缓存读写（uploads/parsed/{doc_id}.validated.json）───────────────


def read_validated_cache(cache_path: Path) -> dict[str, list]:
    try:
        return json.loads(Path(cache_path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_validated_cache(cache_path: Path, cache: dict[str, list]) -> None:
    path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


# ── LLM 调用（可注入 Mock）──────────────────────────────────────────────

_JSON_ARRAY_RE = re.compile(r"\[[\s\S]*\]")
_CODE_FENCE_RE = re.compile(r"```(?:json)?|```")


def extract_knowledge_from_chunk(
    llm, chunk_text: str, covered: list[str] | None = None
) -> list[dict]:
    """从单个文本块提取知识点，返回结构化数组（LLM 调用/解析失败均返回空数组）。"""
    covered = covered or []
    covered_str = f"\n\n已覆盖知识点（不要重复提取）: {'、'.join(covered[:50])}" if covered else ""
    try:
        resp = llm.generate(EXTRACT_SYSTEM, f"待分析文本:\n{chunk_text[:3000]}{covered_str}")
        raw = _CODE_FENCE_RE.sub("", resp).strip()
        m = _JSON_ARRAY_RE.search(raw)
        items = json.loads(m.group(0) if m else raw)
        if not isinstance(items, list):
            return []
        return [it for it in items if isinstance(it, dict) and it.get("name")]
    except Exception:
        return []


__all__ = [
    "DECISION_SYSTEM",
    "EXTRACT_SYSTEM",
    "RuleExtraction",
    "ValidationResult",
    "compute_match_stats",
    "decide_validation_mode",
    "extract_knowledge_from_chunk",
    "get_knowledge_points",
    "pick_sample_count",
    "read_validated_cache",
    "rule_extract",
    "uniform_sample",
    "validate_knowledge",
    "write_validated_cache",
]
