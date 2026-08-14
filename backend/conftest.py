"""pytest 全局配置：sys.path、测试引擎/Session、FastAPI 客户端与登录用户。"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

import models  # noqa: F401  注册全部模型
from db.base import Base
from db.engine import create_app_engine
from db.session import get_db
from main import app
from models import User, Workbook


def _seed_system(eng):
    """测试库中补齐系统账号与系统工作簿（id=0）。"""
    Session = sessionmaker(bind=eng)
    s = Session()
    if s.get(User, 0) is None:
        s.add(User(id=0, username="system", email="system@local", password_hash="!"))
        s.add(Workbook(id=0, user_id=0, name="内置题库", description="系统内置参考题库"))
        s.commit()
    s.close()


class FakeEmbedder:
    """确定性假 embedding（哈希到固定维度），避免测试下载真实模型。"""

    def embed_documents(self, texts):
        return [self._embed(t) for t in texts]

    def embed_query(self, text):
        return self._embed(text)

    def _embed(self, text):
        import hashlib

        dim = 32
        vec = [0.0] * dim
        for ch in text:
            h = hashlib.md5(ch.encode()).digest()
            vec[int.from_bytes(h[:1], "big") % dim] += 1.0
        norm = (sum(v * v for v in vec) ** 0.5) or 1.0
        return [v / norm for v in vec]


@pytest.fixture(autouse=True)
def _isolate_rag(monkeypatch, tmp_path):
    """全局隔离 RAG：假 embedding + 临时 Chroma 目录（上传自动索引不再下载模型）。"""
    from config import settings
    from rag import embedding

    monkeypatch.setattr(settings, "chroma_path", str(tmp_path / "chroma"))
    monkeypatch.setattr(embedding, "get_embedder", lambda: FakeEmbedder())


@pytest.fixture()
def engine(tmp_path):
    db_file = tmp_path / "test.db"
    eng = create_app_engine(f"sqlite:///{db_file.as_posix()}")
    Base.metadata.create_all(eng)
    _seed_system(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session(engine):
    Session = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    s = Session()
    yield s
    s.rollback()
    s.close()


@pytest.fixture()
def client(session):
    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def registered_user(client):
    """注册一个新用户，返回凭据与令牌。"""
    s = uuid.uuid4().hex[:10]
    creds = {"username": f"u{s}", "email": f"{s}@example.com", "password": "password123"}
    resp = client.post("/api/auth/register", json=creds)
    assert resp.status_code == 201
    data = resp.json()
    return {
        "creds": creds,
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "user": data["user"],
    }


@pytest.fixture()
def auth_headers(registered_user):
    return {"Authorization": f"Bearer {registered_user['access_token']}"}


@pytest.fixture()
def workbook(client, auth_headers):
    """创建一个属于当前用户的练习册，返回其 JSON。"""
    resp = client.post(
        "/api/workbooks", json={"name": "测试练习册", "description": ""}, headers=auth_headers
    )
    assert resp.status_code == 201
    return resp.json()
