---
name: rag
description: EStudy 的 RAG（Chroma）开发规范。当编写/修改 chunker、embedding、retriever、Chroma 接入时加载。
---

# rag — RAG（Chroma）开发规范

## 用途
指导 RAG 检索链路的实现，确保 chunk/embedding/检索策略符合 docs，并避免知识污染。

## 何时加载
- 编写/修改 `backend/rag/*`（chunker.py / embedding.py / retriever.py / chroma.py）
- 涉及文档入库、向量化、检索上下文时

## 必须遵守的规范

### 1. 数据流
- 入库：`Document → Text Extraction → Chunk → Embedding → Chroma`
- 查询：`Query → Embedding → Similarity Search → Metadata Filter → Top-K → Agent`

### 2. Chunk 策略
- 采用「章节 → 段落 → 固定长度 Chunk」结构化切分，**优先不破坏原文语义与章节关系**。
- 每个 Chunk 保存 metadata：`chunk_id, course_id, document_id, section, knowledge_id, content`。

### 3. 检索（防知识污染）
- 默认检索带 `course_id + knowledge_id` 过滤，**避免检索到其他课程内容**。
- 统一接口：`retrieve(query, course_id, knowledge_id, top_k) -> [{chunk_id, content, metadata, score}]`。
- Question Agent **不直接操作 Chroma**，只能通过 RAG service。

### 4. RAG 定位
- RAG 是**公共能力服务**，不单独设计复杂 RAG Agent。
- 主要用途：为 Question Agent 提供课程资料上下文（docs 详细设计 Pt.1 §12）。

### 5. Embedding 决策
- P0 先用 Chroma 本地 embedding（免 key），链路通后可按需切千问 text-embedding（需 QWEN key，`.env` 配置 `EMBEDDING_MODEL`）。

### 参考
- docs：`详细设计Pt.1.md` §12、`详细设计Pt.2.md` §4。
