"""助手·导师可调用的薄工具层：只做参数、权限与 Service 适配。"""
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from models.enums import QuestionType
from services import (
    access,
    document_service,
    generation_service,
    knowledge_service,
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
        """生成并审核题目预览；不写数据库。"""
        workbook_id = kwargs["workbook_id"]
        workbook = access.get_visible_workbook(db, user, workbook_id)
        topic = kwargs.pop("topic")
        knowledge_id = kwargs.get("knowledge_id")
        context = f"出题主题：{topic}\n" + rag_service.build_context(
            db, user, workbook_id, knowledge_id
        )
        approved = generation_service.generate_preview(
            llm, workbook.name, topic, kwargs["question_type"],
            kwargs["count"], kwargs["difficulty"], context,
        )
        return {"preview": [q.model_dump(mode="json") for q in approved],
                "approved": len(approved), "saved": False}

    specs = [
        ("search_documents", "按主题语义检索练习册资料", SearchInput, search_documents),
        ("get_knowledge_tree", "读取练习册完整知识树", WorkbookInput, get_knowledge_tree),
        ("get_knowledge_detail", "读取一个知识点的详细内容", KnowledgeInput, get_knowledge_detail),
        ("list_documents", "列出练习册已导入的文档", WorkbookInput, list_documents),
        ("get_questions", "读取用户可见的题库题目", QuestionListInput, get_questions),
        ("generate_questions", "按明确主题生成并审核题目预览；不会写入题库",
         GenerateInput, generate_questions),
    ]
    return [StructuredTool.from_function(name=name, description=desc,
            args_schema=schema, func=fn) for name, desc, schema, fn in specs]
