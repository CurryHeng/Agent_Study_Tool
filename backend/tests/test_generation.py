"""AI 出题 + 审题测试（用 Mock LLM，不真实调用 DeepSeek）。"""
import pytest

from models import Question, User
from models.enums import QuestionSource, QuestionStatus, QuestionType
from schemas.generation import GeneratedOption, GeneratedQuestion
from services import generation_service
from services.llm_service import LLMNotConfiguredError, LLMService, extract_json
from services.question_validator import validate_question


class MockLLM:
    """按顺序返回 JSON 响应的假 LLM。"""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def generate_json(self, system, user):
        self.calls += 1
        if not self.responses:
            return {"questions": []}
        return self.responses.pop(0)


def _valid_choice(content="1+1=?", answer="B"):
    return {
        "type": "single_choice",
        "content": content,
        "answer": answer,
        "analysis": "解析",
        "difficulty": 1,
        "options": [
            {"option_key": "A", "content": "0"},
            {"option_key": "B", "content": "2"},
            {"option_key": "C", "content": "3"},
            {"option_key": "D", "content": "4"},
        ],
    }


# ── 单元：JSON 提取 ─────────────────────────────────────
def test_extract_json_with_fence():
    text = '```json\n{"questions": []}\n```'
    assert extract_json(text) == {"questions": []}


def test_extract_json_with_extra_text():
    text = '好的，以下是题目：\n{"questions": []}\n希望有帮助'
    assert extract_json(text) == {"questions": []}


# ── 单元：业务校验 ───────────────────────────────────────
def test_validator_choice_without_options():
    q = GeneratedQuestion(type=QuestionType.single_choice, content="x", answer="A")
    assert "选择题选项少于 2 个" in validate_question(q)


def test_validator_answer_not_in_options():
    q = GeneratedQuestion(
        type=QuestionType.single_choice,
        content="x",
        answer="E",
        options=[
            GeneratedOption(option_key="A", content="a"),
            GeneratedOption(option_key="B", content="b"),
        ],
    )
    assert any("不在选项" in i for i in validate_question(q))


def test_validator_fill_blank_with_options():
    q = GeneratedQuestion(
        type=QuestionType.fill_blank,
        content="x",
        answer="y",
        options=[GeneratedOption(option_key="A", content="a")],
    )
    assert "非选择题不应携带选项" in validate_question(q)


def test_validator_true_false_accepts_answer_without_options():
    q = GeneratedQuestion(
        type=QuestionType.true_false,
        content="ReAct 会根据工具观察结果继续推理。",
        answer="true",
    )
    assert validate_question(q) == []


# ── 编排：生成 → 审核 → 入库 ─────────────────────────────
def test_generate_single_choice(client, auth_headers, registered_user, session):
    user = session.get(User, registered_user["user"]["id"])
    wb = client.post("/api/workbooks", json={"name": "A"}, headers=auth_headers).json()

    mock = MockLLM(
        [
            {"questions": [_valid_choice("1+1=?"), _valid_choice("2+2=?", "C")]},
            {"passed": True, "score": 0.9, "issues": []},
            {"passed": True, "score": 0.85, "issues": []},
        ]
    )
    result = generation_service.generate_questions(
        session, user, wb["id"], QuestionType.single_choice, 2, llm=mock
    )
    assert len(result) == 2
    assert all(q.type == QuestionType.single_choice for q in result)
    assert all(q.source == QuestionSource.ai for q in result)
    assert len(result[0].options) == 4

    saved = session.query(Question).filter(Question.source == "ai").all()
    assert len(saved) == 2
    assert all(q.status == QuestionStatus.approved for q in saved)


def test_generate_fill_blank(client, auth_headers, registered_user, session):
    user = session.get(User, registered_user["user"]["id"])
    wb = client.post("/api/workbooks", json={"name": "A"}, headers=auth_headers).json()

    fill = {
        "type": "fill_blank",
        "content": "____ 是机器学习的基础。",
        "answer": "数据",
        "analysis": "解析",
        "difficulty": 1,
    }
    mock = MockLLM([{"questions": [fill]}, {"passed": True, "score": 0.9, "issues": []}])
    result = generation_service.generate_questions(
        session, user, wb["id"], QuestionType.fill_blank, 1, llm=mock
    )
    assert len(result) == 1
    assert result[0].options == []


def test_invalid_choice_dropped(client, auth_headers, registered_user, session):
    user = session.get(User, registered_user["user"]["id"])
    wb = client.post("/api/workbooks", json={"name": "A"}, headers=auth_headers).json()

    bad = {"type": "single_choice", "content": "x", "answer": "A", "options": []}
    mock = MockLLM([{"questions": [bad]}])
    result = generation_service.generate_questions(
        session, user, wb["id"], QuestionType.single_choice, 1, llm=mock
    )
    assert result == []


def test_review_fail_retries_then_empty(client, auth_headers, registered_user, session):
    user = session.get(User, registered_user["user"]["id"])
    wb = client.post("/api/workbooks", json={"name": "A"}, headers=auth_headers).json()

    mock = MockLLM(
        [
            {"questions": [_valid_choice()]},
            {"passed": False, "score": 0.3, "issues": ["答案错误"]},
            {"questions": [_valid_choice()]},
            {"passed": False, "score": 0.3, "issues": ["答案错误"]},
            {"questions": [_valid_choice()]},
            {"passed": False, "score": 0.3, "issues": ["答案错误"]},
        ]
    )
    result = generation_service.generate_questions(
        session, user, wb["id"], QuestionType.single_choice, 1, llm=mock
    )
    assert result == []
    assert mock.calls == 6  # 3 次生成 + 3 次审核


def test_generate_with_review_reports_rejected(client, auth_headers, registered_user, session):
    user = session.get(User, registered_user["user"]["id"])
    wb = client.post("/api/workbooks", json={"name": "A"}, headers=auth_headers).json()

    mock = MockLLM(
        [
            {"questions": [_valid_choice("1+1=?"), _valid_choice("错题", "C")]},
            {"passed": True, "score": 0.9, "issues": []},
            {"passed": False, "score": 0.2, "issues": ["答案错误"]},
        ]
    )
    result = generation_service.generate_questions_with_review(
        session, user, wb["id"], QuestionType.single_choice, 2, llm=mock
    )
    assert len(result.saved) == 1
    assert len(result.rejected) == 1
    assert result.rejected[0].review.passed is False
    assert result.rejected[0].review.issues == ["答案错误"]
    assert result.rejected[0].question.content == "错题"


def test_type_mismatch_dropped(client, auth_headers, registered_user, session):
    user = session.get(User, registered_user["user"]["id"])
    wb = client.post("/api/workbooks", json={"name": "A"}, headers=auth_headers).json()

    wrong_type = {
        "type": "fill_blank",
        "content": "x",
        "answer": "y",
    }
    mock = MockLLM([{"questions": [wrong_type]}])
    result = generation_service.generate_questions(
        session, user, wb["id"], QuestionType.single_choice, 1, llm=mock
    )
    assert result == []


def test_generate_similar(client, auth_headers, registered_user, session):
    user = session.get(User, registered_user["user"]["id"])
    wb = client.post("/api/workbooks", json={"name": "A"}, headers=auth_headers).json()
    q = client.post(
        "/api/questions",
        json={
            "workbook_id": wb["id"],
            "type": "single_choice",
            "content": "1+1=?",
            "answer": "B",
            "options": [
                {"option_key": "A", "content": "0"},
                {"option_key": "B", "content": "2"},
            ],
        },
        headers=auth_headers,
    ).json()

    mock = MockLLM([{"questions": [_valid_choice("2+2=?", "C")]}])
    result = generation_service.generate_similar(session, user, q["id"], llm=mock)
    assert result is not None
    assert result.type == QuestionType.single_choice
    assert result.content == "2+2=?"


# ── LLM 未配置 key 的友好错误（回归 #6）─────────────────────
def test_llm_not_configured_raises_503(monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "deepseek_api_key", "")
    service = LLMService()
    with pytest.raises(LLMNotConfiguredError) as exc_info:
        service.generate("system", "user")
    assert exc_info.value.status_code == 503
