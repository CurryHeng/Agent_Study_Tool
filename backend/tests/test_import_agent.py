"""导入 Agent（Document/Knowledge）测试：规则引擎 + 交叉验证 + 图流程 + 上传集成。

移植自 agent-quiz-feature 的导入工作流，LLM 全部用 Mock，不真实调用。
"""
import json
import re

from parsers.base import Section
from services import knowledge_extract_service as kes
from services.structure_extract import (
    build_knowledge_from_structure,
    compute_match_stats,
    detect_language,
    extract_structure_from_text,
    pick_chunk_size,
    split_text_with_lines,
    terms_match,
)
from workflow.import_graph import run_import_graph

# ── Mock LLM ─────────────────────────────────────────────


class MockLLM:
    """generate 返回 JSON 数组字符串（知识点提取）；generate_json 返回预设对象（决策/章节）。"""

    def __init__(self, json_responses=None, text_response="[]"):
        self.json_responses = list(json_responses or [])
        self.text_response = text_response
        self.generate_calls = 0

    def generate_json(self, system, user):
        if self.json_responses:
            return self.json_responses.pop(0)
        return {"accept": True}

    def generate(self, system, user):
        self.generate_calls += 1
        return self.text_response


class SmartExtractLLM(MockLLM):
    """从传入文本中识别"术语N："并原样返回，保证与规则结果高度匹配。"""

    def generate(self, system, user):
        self.generate_calls += 1
        names = re.findall(r"(术语\d+)：", user)
        return json.dumps(
            [{"name": n, "importance": 3, "difficulty": 2} for n in names],
            ensure_ascii=False,
        )


# ── 规则引擎：语言检测 ────────────────────────────────────


def test_detect_language():
    assert detect_language("极限是微积分的基础概念，贯穿整个数学分析课程。") == "zh"
    assert (
        detect_language(
            "Machine learning is a subset of AI. The model is trained on the data "
            "and the parameters are updated in each iteration."
        )
        == "en"
    )
    assert detect_language("") == "other"


# ── 规则引擎：结构提取 ────────────────────────────────────

ZH_DOC = """# 高等数学复习纲要

## 第一章 极限

极限：当 x 趋近于某值时，函数 f(x) 趋近的确定值。
连续函数是指在定义域内任意一点都连续的函数。

## 第二章 导数

导数的几何意义包括：
- 切线斜率
- 瞬时变化率
- 函数单调性判断方法
"""


def test_extract_structure_zh():
    result = extract_structure_from_text(ZH_DOC)
    assert result.language == "zh"
    assert result.title == "高等数学复习纲要"
    assert len(result.headings) == 3
    assert result.headings[1].text == "第一章 极限"

    def_terms = {d.term for d in result.definitions}
    assert "极限" in def_terms
    assert "连续函数" in def_terms

    item_texts = {li.item for li in result.list_items}
    assert "切线斜率" in item_texts
    assert "瞬时变化率" in item_texts


def test_build_knowledge_from_structure():
    knowledge = build_knowledge_from_structure(extract_structure_from_text(ZH_DOC), "高数.md")
    chapters = knowledge["chapters"]
    assert chapters, "应产出至少一个含知识点的章节"
    all_kps = [kp["name"] for ch in chapters for kp in ch["knowledge_points"]]
    assert "极限" in all_kps
    assert "切线斜率" in all_kps
    # 章节内容包含"术语：释义"汇总
    limit_ch = next(
        ch for ch in chapters if any(kp["name"] == "极限" for kp in ch["knowledge_points"])
    )
    assert "极限：" in limit_ch["content"]


def test_terms_match_and_stats():
    assert terms_match("极限", "极限  ")
    assert terms_match("The Limit", "limit")
    assert not terms_match("极限", "导数")
    stats = compute_match_stats([{"name": "极限"}], [{"name": "极限"}, {"name": "导数"}])
    assert stats["recall"] == 1.0
    assert stats["precision"] == 0.5
    assert compute_match_stats([], [{"name": "x"}])["matched"] == 0


# ── 分块 ─────────────────────────────────────────────────


def test_pick_chunk_size_bounds():
    assert pick_chunk_size(0) == 600
    assert pick_chunk_size(100) == 600
    assert pick_chunk_size(10**9) == 2000


def test_split_text_with_lines():
    text = "段落一内容\n\n段落二内容\n\n段落三内容"
    chunks = split_text_with_lines(text, 600)
    assert len(chunks) == 1
    assert chunks[0].start_line == 1

    chunks = split_text_with_lines(text, 10)
    assert len(chunks) == 3
    assert chunks[1].index == 1
    assert "段落二" in chunks[1].text


# ── 抽样 / 短路 / 校验 ────────────────────────────────────


def test_uniform_sample_and_count():
    assert kes.pick_sample_count(5) == 0
    assert kes.pick_sample_count(10) == 3
    assert kes.pick_sample_count(100) == 8
    indices = kes.uniform_sample(10, 3)
    assert indices[0] == 0 and indices[-1] == 9
    assert kes.uniform_sample(3, 5) == [0, 1, 2]


def test_decide_validation_mode():
    # 段落级分块：需多段落才能切出多块
    big = "\n\n".join(["极限是重要概念。" * 50] * 20)
    chunks = split_text_with_lines(big, pick_chunk_size(len(big)))
    assert len(chunks) > 5
    assert kes.decide_validation_mode("短", chunks[:5], 10)[0] == "skip"
    assert kes.decide_validation_mode(big, chunks, 10) == ("validate", "")
    assert kes.decide_validation_mode(big, chunks, 0)[1] == "no-rule-points"


def test_validate_knowledge():
    valid = {
        "chapters": [
            {
                "title": "第一章",
                "knowledge_points": [{"name": "极限", "importance": 3, "difficulty": 2}],
            }
        ]
    }
    assert kes.validate_knowledge(valid).valid
    assert not kes.validate_knowledge("not a dict").valid
    assert not kes.validate_knowledge({"error": "boom"}).valid
    assert not kes.validate_knowledge({"no_chapters": 1}).valid
    bad_imp = {
        "chapters": [{"title": "c", "knowledge_points": [{"name": "x", "importance": 9}]}]
    }
    assert not kes.validate_knowledge(bad_imp).valid


def test_extract_knowledge_from_chunk():
    llm = MockLLM(text_response='[{"name": "极限", "importance": 4, "difficulty": 3}]')
    kps = kes.extract_knowledge_from_chunk(llm, "极限：……")
    assert kps == [{"name": "极限", "importance": 4, "difficulty": 3}]

    garbage = MockLLM(text_response="无法解析的输出")
    assert kes.extract_knowledge_from_chunk(garbage, "任意") == []


# ── 图流程 ───────────────────────────────────────────────


def _long_zh_text(sections: int = 16) -> str:
    """构造足以切出 >5 块的中文复习资料（每节含定义句，规则必有产出）。"""
    parts = []
    for i in range(sections):
        parts.append(f"## 第{i + 1}节 主题{i}")
        parts.append(f"术语{i}：这是术语{i} 的详细定义，用于测试规则提取。" + "补充说明。" * 40)
    return "\n\n".join(parts)


def test_import_graph_accept_rule_result():
    """交叉验证通过 → 采纳规则结果，不做全量提取。"""
    text = _long_zh_text()
    chunks = split_text_with_lines(text, pick_chunk_size(len(text)))
    assert len(chunks) > 5  # 确保走 validate 而非 short 短路

    llm = SmartExtractLLM(json_responses=[{"accept": True}])
    result = run_import_graph(
        title="复习资料",
        plain_text=text,
        sections=[Section(title=f"第{i + 1}节", level=2, paragraphs=[]) for i in range(16)],
        llm=llm,
    )
    assert "交叉验证通过" in result["summary"]
    knowledge = result["knowledge"]
    assert knowledge is not None
    all_kps = [kp["name"] for ch in knowledge["chapters"] for kp in ch["knowledge_points"]]
    assert any(name.startswith("术语") for name in all_kps)
    # 采纳规则结果：全量提取未触发，LLM 提取调用 ≤ 抽样上限 8
    assert llm.generate_calls <= 8


def test_import_graph_document_agent_rebuilds_sections():
    """无章节文档 → Document Agent LLM 识别章节并重建 sections。"""
    llm = MockLLM(
        json_responses=[
            {
                "sections": [
                    {"title": "第一部分", "level": 1, "paragraphs": ["内容一"]},
                    {"title": "第二部分", "level": 1, "paragraphs": ["内容二"]},
                ]
            },
            {"accept": True},
        ],
        text_response='[{"name": "知识点A", "importance": 3, "difficulty": 2}]',
    )
    result = run_import_graph(
        title="无结构文档",
        plain_text="内容一\n\n内容二",
        sections=[Section(title="全文", level=1, paragraphs=["内容一", "内容二"])],
        llm=llm,
    )
    assert [s.title for s in result["sections"]] == ["第一部分", "第二部分"]
    assert result["knowledge"] is not None


def test_import_graph_full_extract_on_short_doc():
    """短文档短路 → 全量提取，规则点与 LLM 点合并去重。"""
    llm = MockLLM(text_response='[{"name": "LLM知识点", "importance": 3, "difficulty": 2}]')
    result = run_import_graph(
        title="短文档",
        plain_text="极限：函数趋近的确定值。",
        sections=[Section(title="全文", level=1, paragraphs=["极限：函数趋近的确定值。"])],
        llm=llm,
    )
    knowledge = result["knowledge"]
    assert knowledge is not None
    all_kps = [kp["name"] for ch in knowledge["chapters"] for kp in ch["knowledge_points"]]
    assert "LLM知识点" in all_kps
    assert "极限" in all_kps  # 规则结果兜底保留


def test_import_graph_llm_down_still_returns_rule_result():
    """提取 LLM 全挂 → 样本无产出 → 保守全量也失败 → 至少保留规则兜底知识点。"""

    class BoomLLM(MockLLM):
        def generate(self, system, user):
            raise RuntimeError("LLM down")

        def generate_json(self, system, user):
            raise RuntimeError("LLM down")

    text = _long_zh_text()
    llm = BoomLLM()
    result = run_import_graph(
        title="复习资料",
        plain_text=text,
        sections=[Section(title=f"第{i + 1}节", level=2, paragraphs=[]) for i in range(16)],
        llm=llm,
    )
    # 全量提取中规则兜底仍在
    knowledge = result["knowledge"]
    assert knowledge is not None
    all_kps = [kp["name"] for ch in knowledge["chapters"] for kp in ch["knowledge_points"]]
    assert any(name.startswith("术语") for name in all_kps)


# ── 上传集成 ─────────────────────────────────────────────


def test_upload_document_with_import_agents(
    client, auth_headers, workbook, session, monkeypatch
):
    """配置 API key 后，上传文档经导入 Agent 提取知识点并入库。"""
    from config import settings

    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(
        "workflow.import_graph.get_llm",
        lambda: MockLLM(text_response='[{"name": "LLM提取点", "importance": 3, "difficulty": 2}]'),
    )

    md = "# 优化方法\n\n## 梯度下降\n\n梯度下降：沿负梯度方向迭代更新参数的优化算法。\n"
    resp = client.post(
        "/api/documents/upload",
        data={"workbook_id": str(workbook["id"])},
        files={"file": ("opt.md", md.encode("utf-8"), "text/markdown")},
        headers=auth_headers,
    )
    assert resp.status_code == 201

    nodes = client.get(
        f"/api/knowledge?workbook_id={workbook['id']}", headers=auth_headers
    ).json()
    names = [n["name"] for n in nodes]
    assert "优化方法" in names  # 章节树照常建立
    assert "LLM提取点" in names  # LLM 提取的知识点入库
    assert "梯度下降" in names  # 规则提取的知识点入库


def test_upload_document_without_api_key_skips_agents(
    client, auth_headers, workbook, monkeypatch
):
    """未配置 API key 时保持原有确定性行为（不调用 LLM）。"""
    from config import settings

    monkeypatch.setattr(settings, "deepseek_api_key", "")

    def _boom():
        raise AssertionError("不应调用 LLM")

    monkeypatch.setattr("workflow.import_graph.get_llm", _boom)

    md = "# 优化方法\n\n## 梯度下降\n\n梯度下降：沿负梯度方向迭代更新参数。\n"
    resp = client.post(
        "/api/documents/upload",
        data={"workbook_id": str(workbook["id"])},
        files={"file": ("opt.md", md.encode("utf-8"), "text/markdown")},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    nodes = client.get(
        f"/api/knowledge?workbook_id={workbook['id']}", headers=auth_headers
    ).json()
    names = [n["name"] for n in nodes]
    assert "优化方法" in names
    assert "梯度下降" in names  # 确定性章节树仍有
