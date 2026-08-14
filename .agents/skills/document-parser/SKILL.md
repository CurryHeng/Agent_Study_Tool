---
name: document-parser
description: StudyForge 文档解析（PDF/MD/Word/PPT/图片）开发规范。当编写/修改 parser、Document Representation、文件上传解析逻辑时加载。
---

# document-parser — 文档解析开发规范

## 用途
指导多格式文档解析器的实现，统一为 Document Representation，解耦文件解析与 Agent 内容理解。

## 何时加载
- 编写/修改 `backend/parsers/*`（pdf.py / markdown.py / word.py / ppt.py / image.py）
- 涉及文件上传、格式识别、解析流程时

## 必须遵守的规范

### 1. 支持格式与库（P0）
| 格式 | 库 |
|---|---|
| PDF | pypdf |
| Markdown | markdown-it-py（已装）|
| Word (.docx) | python-docx |
| PPT (.pptx) | python-pptx |
| 图片 | 千问视觉（dashscope）|

### 2. 统一接口（硬约束）
- 所有 parser 实现统一接口 `parse(file) -> Document`。
- 新增格式只需新增 parser，**不修改 Agent 层**。

### 3. Document Representation
```text
Document
├── id / title / source_type / metadata
└── sections[]
    ├── title / level
    ├── paragraphs[] / tables[] / images[]
```

### 4. 职责边界（重要）
- **Parser**：把文件变成可处理的结构化数据（普通程序，确定性）。
- **Document Agent**：理解这些数据是什么（章节识别/内容理解，Agent）。
- 文件解析与 Agent 处理**分离**。

### 5. 文件校验
- 上传时先检查：存在性 → 格式 → 大小 → 解析。
- 文件上传走 `python-multipart`；原始文件存 `data/uploads/`。

### 参考
- docs：`详细设计Pt.2.md` §3、`详细设计Pt.1.md` §9/§10。
