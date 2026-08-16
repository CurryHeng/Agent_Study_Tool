"""文档上传 / 解析 / 知识提取业务逻辑。"""
import json
from dataclasses import asdict
from pathlib import Path

from sqlalchemy.orm import Session

from config import settings
from db.uow import UnitOfWork
from models import Document, User
from models.enums import DocumentStatus, QuestionType
from parsers.factory import detect_type, parse_file
from repositories import document_repository
from schemas.document import DocumentDetailOut, DocumentOut, SectionOut
from services import access, ai_settings, knowledge_service


def _upload_dir() -> Path:
    return Path(settings.upload_dir)


def _parsed_path(doc_id: int) -> Path:
    return _upload_dir() / "parsed" / f"{doc_id}.json"


def _validated_cache_path(doc_id: int) -> Path:
    """导入 Agent 抽样验证缓存（uploads/parsed/{doc_id}.validated.json）。"""
    return _upload_dir() / "parsed" / f"{doc_id}.validated.json"


def _run_import_agents(doc_id: int, parsed) -> dict | None:
    """运行导入 Agent（Document/Knowledge）：LLM 章节理解 + 知识点提取。

    仅在配置了 DEEPSEEK_API_KEY 时启用；失败不阻断上传（解析与章节树已成功，
    按无 LLM 的确定性结果继续）。返回知识 dict 或 None。
    """
    if not settings.deepseek_api_key:
        return None
    try:
        from workflow.import_graph import run_import_graph

        plain_text = "\n\n".join(p for s in parsed.sections for p in s.paragraphs)
        result = run_import_graph(
            title=parsed.title,
            plain_text=plain_text,
            sections=parsed.sections,
            cache_path=_validated_cache_path(doc_id),
        )
        parsed.sections = result["sections"] or parsed.sections
        return result["knowledge"]
    except Exception:
        return None


def _save_parsed(doc_id: int, parsed) -> None:
    path = _parsed_path(doc_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(parsed), ensure_ascii=False), encoding="utf-8")


def _load_sections(doc_id: int) -> list[SectionOut]:
    path = _parsed_path(doc_id)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [SectionOut(**s) for s in data.get("sections", [])]


def read_parsed_sections(doc_id: int) -> list:
    """读取已解析的章节（供 RAG 切块使用），返回 parsers.base.Section 列表。"""
    from parsers.base import Section

    path = _parsed_path(doc_id)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        Section(title=s["title"], level=s["level"], paragraphs=s.get("paragraphs", []))
        for s in data.get("sections", [])
    ]


def _to_detail(
    doc: Document, sections: list[SectionOut], generated_questions=None
) -> DocumentDetailOut:
    return DocumentDetailOut(
        id=doc.id,
        workbook_id=doc.workbook_id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_path=doc.file_path,
        file_size=doc.file_size,
        status=doc.status,
        created_at=doc.created_at,
        sections=sections,
        generated_questions=generated_questions,
    )




def _auto_generate_questions(
    db: Session,
    user: User,
    workbook,
    parsed,
    sections: list[SectionOut],
    *,
    question_type: str,
    count: int,
    difficulty: int,
    scope: str | None,
):
    """导入后自动生成题目预览（不入库）。失败不阻断上传。"""
    try:
        from services import generation_service
        from services.llm_service import get_llm

        if not settings.deepseek_api_key and not ai_settings.get_text_config().get("api_key"):
            return None

        try:
            qtype = QuestionType(question_type)
        except ValueError:
            qtype = QuestionType.single_choice

        topic = scope or parsed.title or "本章内容"
        context_parts = [f"文档标题：{parsed.title}"]
        for s in sections:
            if scope and scope not in s.title:
                continue
            context_parts.append(f"章节：{s.title}\n" + "\n".join(s.paragraphs))
        context = "\n".join(context_parts)[:6000]

        return generation_service.generate_preview(
            get_llm(), workbook.name, topic, qtype, count, difficulty, context
        )
    except Exception:
        return None


def upload_document(
    db: Session,
    user: User,
    workbook_id: int,
    filename: str,
    content: bytes,
    *,
    auto_generate: bool = False,
    question_type: str = "single_choice",
    count: int = 5,
    difficulty: int = 1,
    scope: str | None = None,
) -> DocumentDetailOut:
    workbook = access.get_owned_workbook(db, user, workbook_id)

    file_type = detect_type(filename)
    if file_type is None:
        raise access.AccessError(422, "不支持的文件格式（支持 PDF/Markdown/Word/PPT/图片）")
    if file_type == "image":
        mm_cfg = ai_settings.get_multimodal_config()
        if not mm_cfg["api_key"] and mm_cfg["provider"] != "ollama":
            raise access.AccessError(503, "多模态 API 未配置，请先在设置页配置")
    if len(content) > settings.max_file_size:
        raise access.AccessError(413, "文件过大")

    doc = document_repository.create(db, workbook_id, filename, file_type, "")
    db.flush()

    UPLOAD_DIR = _upload_dir()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(filename).suffix.lower()
    file_path = UPLOAD_DIR / f"{doc.id}{ext}"
    file_path.write_bytes(content)
    doc.file_path = str(file_path)

    try:
        parsed = parse_file(str(file_path), file_type)
        parsed.title = Path(filename).stem
    except Exception as exc:
        doc.status = DocumentStatus.failed
        db.flush()
        raise access.AccessError(422, f"文档解析失败：{exc}") from exc

    knowledge = _run_import_agents(doc.id, parsed)
    _save_parsed(doc.id, parsed)
    root = knowledge_service.import_sections(db, workbook_id, doc.id, parsed.title, parsed.sections)
    if knowledge:
        knowledge_service.import_knowledge_points(db, workbook_id, doc.id, root, knowledge)
    doc.status = DocumentStatus.success
    db.flush()

    # 上传后自动构建向量索引（RAG 检索依赖）；失败不阻断上传，可稍后手动重建。
    try:
        from services import rag_service

        rag_service.index_document(db, user, doc.id)
    except Exception:
        pass

    sections = [
        SectionOut(title=s.title, level=s.level, paragraphs=s.paragraphs)
        for s in parsed.sections
    ]

    generated_questions = None
    if auto_generate:
        generated_questions = _auto_generate_questions(
            db, user, workbook, parsed, sections,
            question_type=question_type, count=count,
            difficulty=difficulty, scope=scope,
        )

    return _to_detail(doc, sections, generated_questions)


def list_documents(db: Session, user: User, workbook_id: int) -> list[DocumentOut]:
    access.get_visible_workbook(db, user, workbook_id)
    return document_repository.list_by_workbook(db, workbook_id)


def get_document(db: Session, user: User, document_id: int) -> DocumentDetailOut:
    doc = document_repository.get_by_id(db, document_id)
    if doc is None:
        raise access.AccessError(404, "文档不存在")
    access.get_visible_workbook(db, user, doc.workbook_id)
    return _to_detail(doc, _load_sections(doc.id))


def delete_document(db: Session, user: User, document_id: int) -> None:
    doc = document_repository.get_by_id(db, document_id)
    if doc is None:
        raise access.AccessError(404, "文档不存在")
    access.get_owned_workbook(db, user, doc.workbook_id)

    # #57 UoW：先清理 Chroma 向量，再提交 SQLite 删除；任一步失败都回滚
    from services import rag_service

    with UnitOfWork(db) as uow:
        uow.add_pre_commit(lambda: rag_service.delete_document_vectors(doc.id))
        document_repository.delete(db, doc)
