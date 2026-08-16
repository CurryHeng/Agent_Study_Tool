"""助手·导师可调用的薄工具层：只做参数、权限与 Service 适配。"""
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from models.enums import QuestionType
from schemas.knowledge import KnowledgeCreate, KnowledgeUpdate
from services import (
    access,
    document_service,
    generation_service,
    knowledge_service,
    proposal_service,
    question_service,
    rag_service,
)


class WorkbookInput(BaseModel):
    workbook_id: int = Field(description="要读取的练习册 ID")


class SearchInput(WorkbookInput):
    query: str = Field(description="要在学习资料中检索的具体主题或问题")
    knowledge_id: int | None = Field(default=None, description="可选的知识点 ID")
    top_k: int = Field(default=4, ge=1, le=10, description="返回片段数")


class KnowledgeInput(BaseModel):
    knowledge_id: int = Field(description="要读取详情的知识点 ID")


class AddKnowledgeInput(WorkbookInput):
    name: str = Field(min_length=1, max_length=255, description="新知识点名称")
    parent_id: int | None = Field(default=None, description="可选的父知识点 ID")
    description: str | None = Field(default=None, description="知识点描述")
    level: int = Field(default=0, ge=0, description="知识点层级")


class UpdateKnowledgeInput(KnowledgeInput):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    parent_id: int | None = None
    description: str | None = None
    level: int | None = Field(default=None, ge=0)


class QuestionListInput(BaseModel):
    workbook_id: int | None = Field(default=None, description="可选的练习册 ID")


class GenerateInput(WorkbookInput):
    topic: str = Field(description="明确的出题主题，禁止留空或只写‘这里’")
    question_type: QuestionType = Field(default=QuestionType.single_choice, description="题型")
    count: int = Field(default=5, ge=1, le=20, description="生成题目数量")
    difficulty: int = Field(default=1, ge=1, le=5, description="难度 1 到 5")
    knowledge_id: int | None = Field(default=None, description="可选的知识点 ID")


def build_tools(db, user, llm) -> list[StructuredTool]:
    """为单次请求构建绑定当前数据库会话和用户的工具。"""

    def search_documents(**kwargs):
        return rag_service.retrieve(db, user, **kwargs)

    def get_knowledge_tree(workbook_id: int):
        nodes = knowledge_service.list_knowledge(db, user, workbook_id)
        return [{"id": n.id, "parent_id": n.parent_id, "name": n.name,
                 "description": n.description, "level": n.level} for n in nodes]

    def get_knowledge_detail(knowledge_id: int):
        node = knowledge_service.get_knowledge(db, user, knowledge_id)
        return {"id": node.id, "workbook_id": node.workbook_id,
                "parent_id": node.parent_id, "name": node.name,
                "description": node.description, "level": node.level}

    def list_documents(workbook_id: int):
        return [item.model_dump(mode="json") for item in
                document_service.list_documents(db, user, workbook_id)]

    def get_questions(workbook_id: int | None = None):
        return [item.model_dump(mode="json") for item in
                question_service.list_questions(db, user, workbook_id)]

    def generate_questions(**kwargs):
        """生成并审核题目预览，保存提案但不写题库。"""
        workbook_id = kwargs["workbook_id"]
        workbook = access.get_owned_workbook(db, user, workbook_id)
        topic = kwargs.pop("topic")
        knowledge_id = kwargs.get("knowledge_id")
        context = f"出题主题：{topic}\n" + rag_service.build_context(
            db, user, workbook_id, knowledge_id
        )
        approved = generation_service.generate_preview(
            llm, workbook.name, topic, kwargs["question_type"],
            kwargs["count"], kwargs["difficulty"], context,
        )
        preview = [q.model_dump(mode="json") for q in approved]
        return proposal_service.create(
            user.id, "generate_questions", {"workbook_id": workbook_id,
            "workbook_name": workbook.name}, {"before": None, "after":
            {"questions": preview}}, f"向题库新增 {len(preview)} 道审核通过的题目",
            {"workbook_id": workbook_id, "knowledge_id": knowledge_id,
            "questions": preview},
        )

    def add_knowledge_node(**kwargs):
        data = KnowledgeCreate.model_validate(kwargs)
        access.get_owned_workbook(db, user, data.workbook_id)
        return proposal_service.create(
            user.id, "add_knowledge_node", {"workbook_id": data.workbook_id},
            {"before": None, "after": data.model_dump(mode="json")},
            f"新增知识点“{data.name}”", data.model_dump(mode="json"),
        )

    def update_knowledge_node(knowledge_id: int, **kwargs):
        node = access.get_owned_knowledge(db, user, knowledge_id)
        changes = KnowledgeUpdate.model_validate(kwargs).model_dump(exclude_unset=True)
        return proposal_service.create(
            user.id, "update_knowledge_node", {"knowledge_id": node.id,
            "name": node.name}, {"before": {key: getattr(node, key) for key in changes},
            "after": changes}, f"修改知识点“{node.name}”", {"knowledge_id": node.id,
            "changes": changes},
        )

    def delete_knowledge_node(knowledge_id: int):
        node = access.get_owned_knowledge(db, user, knowledge_id)
        return proposal_service.create(
            user.id, "delete_knowledge_node", {"knowledge_id": node.id,
            "name": node.name}, {"before": {"name": node.name,
            "description": node.description}, "after": None},
            f"删除知识点“{node.name}”", {"knowledge_id": node.id},
        )

    specs = [
        ("search_documents", "按主题语义检索练习册资料", SearchInput, search_documents),
        ("get_knowledge_tree", "读取练习册完整知识树", WorkbookInput, get_knowledge_tree),
        ("get_knowledge_detail", "读取一个知识点的详细内容", KnowledgeInput, get_knowledge_detail),
        ("list_documents", "列出练习册已导入的文档", WorkbookInput, list_documents),
        ("get_questions", "读取用户可见的题库题目", QuestionListInput, get_questions),
        ("generate_questions", "生成并审核题目提案；用户确认前不会写入题库",
         GenerateInput, generate_questions),
        ("add_knowledge_node", "提出新增知识点；用户确认前不会写入",
         AddKnowledgeInput, add_knowledge_node),
        ("update_knowledge_node", "提出修改知识点；用户确认前不会写入",
         UpdateKnowledgeInput, update_knowledge_node),
        ("delete_knowledge_node", "提出删除知识点；用户确认前不会删除",
         KnowledgeInput, delete_knowledge_node),
    ]
    return [StructuredTool.from_function(name=name, description=desc,
            args_schema=schema, func=fn) for name, desc, schema, fn in specs]
