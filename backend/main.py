"""FastAPI 应用入口。"""
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.agent import router as agent_router
from api.auth import router as auth_router
from api.conversations import router as conversations_router
from api.documents import router as documents_router
from api.history import router as history_router
from api.knowledge import router as knowledge_router
from api.knowledge_graph import router as knowledge_graph_router
from api.questions import router as questions_router
from api.rag import router as rag_router
from api.review import router as review_router
from api.settings import router as settings_router
from api.stats import router as stats_router
from api.workbooks import router as workbooks_router
from api.wrong_records import router as wrong_records_router
from services.access import AccessError

app = FastAPI(title="EStudy", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175", "http://127.0.0.1:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(conversations_router)
app.include_router(workbooks_router)
app.include_router(questions_router)
app.include_router(knowledge_router)
app.include_router(knowledge_graph_router)
app.include_router(documents_router)
app.include_router(history_router)
app.include_router(rag_router)
app.include_router(review_router)
app.include_router(agent_router)
app.include_router(wrong_records_router)
app.include_router(stats_router)
app.include_router(settings_router)


@app.exception_handler(AccessError)
def access_error_handler(_request: Request, exc: AccessError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "timestamp": datetime.now(UTC).isoformat()}
