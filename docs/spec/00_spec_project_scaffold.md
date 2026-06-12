# 00_SPEC_PROJECT_SCAFFOLD — LawGo Traffic

**Product name:** LawGo Traffic  
**Tagline:** AI legal assistant for Vietnam traffic law  
**Purpose of this spec:** Hướng dẫn LLM/AI coding agent tạo nhanh khung repo ban đầu cho dự án LawGo Traffic.

---

## 1. Product Context

LawGo Traffic là AI legal assistant chuyên về **Luật giao thông đường bộ Việt Nam**. Hệ thống không chỉ là chatbot RAG thông thường, mà hướng đến mô hình **Agent + Tool-based GraphRAG**.

Mục tiêu sản phẩm:

- Trả lời câu hỏi về luật giao thông Việt Nam bằng ngôn ngữ dễ hiểu.
- Phân tích tình huống vi phạm thực tế.
- Tra mức phạt, quyền của người tham gia giao thông, thẩm quyền xử phạt, thủ tục nộp phạt / lấy lại xe / khiếu nại.
- Luôn trả lời có căn cứ pháp lý: văn bản, điều, khoản, điểm.

MVP ưu tiên:

1. Legal GraphRAG Tool
2. Situation Analyzer
3. Rights Checker
4. Fine Lookup / Fine Calculator cơ bản
5. Web chat API đơn giản

Các phần để sau:

- Voice STT/TTS
- Road Intelligence / Overpass API
- User profile memory nâng cao
- Neo4j production graph
- OCR / PDF scan parser

---

## 2. Core Architecture

Kiến trúc tổng thể:

```text
User
→ Main Agent / API
→ legal_rag_search tool
→ GraphRAG engine
→ Evidence + citations
→ Main Agent generates final answer
```

RAG không phải là toàn bộ app. RAG là **một tool** hoặc **một sub-agent**.

Main Agent chịu trách nhiệm:

- Nhận câu hỏi người dùng.
- Phân loại intent.
- Quyết định có cần gọi `legal_rag_search` không.
- Gọi thêm các tool khác nếu cần: `fine_calculator`, `rights_checker`, `authority_checker`, `procedure_lookup`.
- Tổng hợp câu trả lời cuối.

GraphRAG Tool chịu trách nhiệm:

- Truy xuất căn cứ pháp lý.
- Tìm graph paths liên quan.
- Map kết quả về Điều/Khoản/Điểm.
- Trả evidence có citation cho Agent.

---

## 3. Recommended Tech Stack for Scaffold

Use Python-first backend.

```text
Language: Python 3.11+
Backend API: FastAPI
UI: Streamlit
Agent orchestration: LangGraph (ReAct loop)
Document parser: python-docx + regex
GraphRAG: LightRAG
Vector DB: Qdrant Cloud (stub locally first, point to Cloud in prod)
Graph store: Neo4j AuraDB Free (semantic graph)
Keyword Search: BM25s placeholder / local stub first
Metadata / relational store: Supabase PostgreSQL
File storage: Supabase Storage
Cache/session: Redis placeholder, optional in scaffold
Testing: pytest
Code quality: ruff, mypy optional
Env management: uv or pip + requirements.txt
Docker: optional, docker-compose for local dev
```

Do not set up heavy infra in the first scaffold. The first scaffold should run locally with simple commands.

---

## 4. Repository Structure

Create this structure:

```text
lawgo-traffic/
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── docker-compose.yml
│
├── data/
│   ├── raw/
│   │   └── .gitkeep
│   ├── extracted/
│   │   └── .gitkeep
│   ├── parsed/
│   │   └── .gitkeep
│   ├── chunks/
│   │   └── .gitkeep
│   ├── graph/
│   │   └── .gitkeep
│   └── eval/
│       └── golden_questions.sample.json
│
├── scripts/
│   ├── ingest_docx.py
│   ├── build_chunks.py
│   ├── build_graph_index.py
│   └── run_eval.py
│
├── src/
│   └── lawgo_traffic/
│       ├── __init__.py
│       │
│       ├── config.py
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── main.py
│       │   ├── schemas.py
│       │   └── routes_chat.py
│       │
│       ├── agent/
│       │   ├── __init__.py
│       │   ├── main_agent.py
│       │   ├── intent_router.py
│       │   └── prompts.py
│       │
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── docx_extractor.py
│       │   ├── legal_parser.py
│       │   ├── chunk_builder.py
│       │   └── id_utils.py
│       │
│       ├── graph/
│       │   ├── __init__.py
│       │   ├── schema.py
│       │   ├── structural_graph_builder.py
│       │   ├── semantic_graph_builder.py
│       │   └── graph_store.py
│       │
│       ├── rag/
│       │   ├── __init__.py
│       │   ├── legal_rag_search.py
│       │   ├── lightrag_adapter.py
│       │   ├── vector_retriever.py
│       │   ├── bm25_retriever.py
│       │   ├── citation_mapper.py
│       │   └── result_types.py
│       │
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── fine_calculator.py
│       │   ├── rights_checker.py
│       │   ├── authority_checker.py
│       │   └── procedure_lookup.py
│       │
│       ├── eval/
│       │   ├── __init__.py
│       │   ├── metrics.py
│       │   └── evaluator.py
│       │
│       ├── voice/
│       │   ├── __init__.py
│       │   ├── stt_adapter.py       # STT interface (PhoWhisper stub)
│       │   └── tts_adapter.py       # TTS interface (Edge-TTS stub)
│       │
│       └── utils/
│           ├── __init__.py
│           ├── jsonl.py
│           └── text_normalizer.py
│
└── tests/
    ├── test_legal_parser.py
    ├── test_chunk_builder.py
    ├── test_legal_rag_search.py
    └── fixtures/
        └── sample_law_text.txt
```

---

## 5. Modules to Scaffold

### 5.1 `config.py`

Create a typed settings object.

Required env variables:

```text
APP_NAME=LawGo Traffic
APP_ENV=local
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=multilingual-e5-large
DATA_DIR=./data
LIGHTRAG_WORKING_DIR=./data/graph/lightrag

# Qdrant Cloud
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# Neo4j AuraDB Free
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=

# Supabase
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_BUCKET=lawgo-traffic-docs

# Voice (placeholder, not required for scaffold boot)
VOICE_ENABLED=false
STT_MODEL=phowhisper
TTS_VOICE=vi-VN-HoaiMyNeural
```

For scaffold, env values can be optional with safe defaults.

---

### 5.2 `docx_extractor.py`

Purpose:

- Read `.docx` files from `data/raw`.
- Extract paragraphs and tables if possible.
- Save normalized text to `data/extracted/*.txt` or `*.json`.

Function signatures:

```python
def extract_docx_to_text(input_path: str) -> str:
    ...


def extract_all_docx(raw_dir: str, output_dir: str) -> list[str]:
    ...
```

Do not implement OCR. Word files are assumed clean.

---

### 5.3 `legal_parser.py`

Purpose:

Parse Vietnamese legal document structure:

```text
Document → Chapter → Section → Article → Clause → Point
```

Required output:

```python
class LegalUnit:
    doc_id: str
    document_title: str | None
    chapter: str | None
    section: str | None
    article: str | None
    article_title: str | None
    clause: str | None
    point: str | None
    text: str
```

Initial regex patterns:

```text
Chapter: ^Chương\s+[IVXLCDM]+|^CHƯƠNG\s+[IVXLCDM]+
Section: ^Mục\s+\d+|^MỤC\s+\d+
Article: ^Điều\s+\d+[a-zA-Z]?\.
Clause: ^\d+\.
Point: ^[a-zđ]\)
```

Parser must preserve legal hierarchy metadata.

---

### 5.4 `chunk_builder.py`

Purpose:

Create parent-child legal chunks.

Rules:

```text
Parent chunk = Article-level chunk
Child chunk = Clause-level or Point-level chunk
```

Each child chunk must include legal path in `text_for_search`.

Example child chunk:

```json
{
  "chunk_id": "nd168_2024_dieu_7_khoan_4_diem_a",
  "parent_id": "nd168_2024_dieu_7",
  "chunk_type": "POINT",
  "text_raw": "Không chấp hành hiệu lệnh của đèn tín hiệu giao thông...",
  "text_for_search": "Nghị định 168/2024/NĐ-CP. Điều 7. Khoản 4. Điểm a. Không chấp hành hiệu lệnh của đèn tín hiệu giao thông...",
  "metadata": {
    "document_title": "Nghị định 168/2024/NĐ-CP",
    "article": "Điều 7",
    "clause": "Khoản 4",
    "point": "Điểm a"
  }
}
```

Outputs:

```text
data/chunks/parents.jsonl
data/chunks/children.jsonl
```

---

### 5.5 `graph/schema.py`

Define graph node and edge types.

Node types:

```text
Document
Article
Clause
Point
Violation
Penalty
VehicleType
Authority
Right
Procedure
Condition
LegalConcept
```

Edge types:

```text
HAS_ARTICLE
HAS_CLAUSE
HAS_POINT
REGULATES
HAS_PENALTY
HAS_ADDITIONAL_PENALTY
APPLIES_TO
HAS_AUTHORITY
HAS_RIGHT
HAS_PROCEDURE
HAS_CONDITION
REFERENCES
AMENDS
REPLACES
```

---

### 5.6 `structural_graph_builder.py`

Purpose:

Build deterministic legal structure graph from parsed chunks.

Must build:

```text
Document → Article → Clause → Point
```

This is rule-based and must not rely on LLM.

---

### 5.7 `lightrag_adapter.py`

Purpose:

Wrap LightRAG so the rest of the app does not depend directly on LightRAG API.

Initial class:

```python
class LightRAGAdapter:
    def __init__(self, working_dir: str):
        ...

    def index_chunks(self, chunks: list[dict]) -> None:
        ...

    def query(self, query: str, mode: str = "hybrid") -> dict:
        ...
```

For scaffold, implementation can be a stub returning empty results.

Later implementation will call actual LightRAG.

---

### 5.8 `legal_rag_search.py`

This is the core tool interface.

Function:

```python
def legal_rag_search(
    query: str,
    intent: str | None = None,
    filters: dict | None = None,
) -> LegalRAGSearchResult:
    ...
```

Expected output:

```json
{
  "query": "Xe máy vượt đèn đỏ phạt bao nhiêu?",
  "intent": "fine_lookup",
  "answer_basis": [
    {
      "content": "...",
      "document": "Nghị định 168/2024/NĐ-CP",
      "article": "Điều ...",
      "clause": "Khoản ...",
      "point": "Điểm ...",
      "source_chunk_id": "..."
    }
  ],
  "graph_paths": [
    "vượt đèn đỏ -> HAS_PENALTY -> phạt tiền ..."
  ],
  "confidence": 0.0,
  "warnings": []
}
```

GraphRAG Tool must not generate the final user-facing answer. It returns evidence only.

---

### 5.9 `intent_router.py`

Supported initial intents:

```text
fine_lookup
multi_violation
rights_lookup
authority_lookup
procedure_lookup
legal_explain
out_of_scope
```

For scaffold, implement keyword-based routing first.

Later, replace with LLM classifier.

---

### 5.10 `main_agent.py`

Purpose:

- Receive user question.
- Route intent.
- Call `legal_rag_search` if legal evidence is needed.
- Produce final response using retrieved evidence.

For scaffold, can return a simple template response.

Do not implement full ReAct yet.

---

### 5.11 `voice/stt_adapter.py` and `voice/tts_adapter.py`

Purpose:

- Provide stable interface so the rest of the app can accept voice input without knowing the STT/TTS implementation.
- In scaffold, both are **stubs** — no actual model loaded, just the interface.

```python
class STTAdapter:
    def transcribe(self, audio_bytes: bytes, language: str = "vi") -> str:
        # stub: return empty string
        return ""

class TTSAdapter:
    def synthesize(self, text: str, voice: str = "vi-VN-HoaiMyNeural") -> bytes:
        # stub: return empty bytes
        return b""
```

Voice is gated by `VOICE_ENABLED` env var. When false, the API accepts text-only input. When true, the STT adapter converts voice → text before passing to the agent, and TTS adapter converts agent response → audio.

The `/chat` endpoint must accept both `message` (text) and `audio` (base64, optional) in the same request schema.

---

### 5.12 `api/main.py`

Create FastAPI app with health endpoint.

Required endpoints:

```text
GET /health
POST /chat
POST /tools/legal-rag-search
```

`POST /chat` request:

```json
{
  "message": "Xe máy vượt đèn đỏ phạt bao nhiêu?",
  "audio": null,
  "session_id": "optional-session-id"
}
```

`message` and `audio` are mutually exclusive. If `audio` is provided (base64-encoded), STTAdapter transcribes it first. `VOICE_ENABLED=false` causes the endpoint to reject `audio` input with 400.

`POST /tools/legal-rag-search` request:

```json
{
  "query": "Xe máy vượt đèn đỏ phạt bao nhiêu?",
  "intent": "fine_lookup",
  "filters": {}
}
```

---

## 6. Scripts to Scaffold

### `scripts/ingest_docx.py`

CLI:

```bash
python scripts/ingest_docx.py --input data/raw --output data/extracted
```

### `scripts/build_chunks.py`

CLI:

```bash
python scripts/build_chunks.py --input data/extracted --output data/chunks
```

### `scripts/build_graph_index.py`

CLI:

```bash
python scripts/build_graph_index.py --chunks data/chunks/children.jsonl
```

### `scripts/run_eval.py`

CLI:

```bash
python scripts/run_eval.py --questions data/eval/golden_questions.sample.json
```

---

## 7. Docker Compose for Scaffold

Create `docker-compose.yml` with optional services:

```text
qdrant
redis
```

Do not require these services to run the initial API. They are placeholders for later.

---

## 8. README Requirements

README must include:

- Product name: LawGo Traffic
- One-line description
- Architecture overview
- Setup instructions
- Folder explanation
- Commands:
  - install dependencies
  - run API
  - ingest documents
  - build chunks
  - run legal RAG search endpoint
- Current limitations

Sample quickstart:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn lawgo_traffic.api.main:app --reload
```

---

## 9. Acceptance Criteria for Scaffold

The generated repo is acceptable when:

1. Repo structure matches this spec.
2. FastAPI app starts successfully.
3. `/health` returns status OK.
4. `POST /tools/legal-rag-search` returns valid JSON with fields:
   - `query`
   - `intent`
   - `answer_basis`
   - `graph_paths`
   - `confidence`
   - `warnings`
5. Parser and chunk builder modules exist.
6. Unit test placeholders exist.
7. README explains how to run the project.
8. No heavy external dependency is mandatory just to boot the app.

---

## 10. What Not to Build in Spec 00

Do not implement yet:

- Full LightRAG integration
- Full LLM extraction
- Neo4j / Apache AGE
- Voice STT/TTS
- Road lookup
- OCR / image parsing
- Production authentication
- Complex LangGraph ReAct loop

Spec 00 only creates the project skeleton and stable module boundaries.

---

## 11. Naming Conventions

Project display name:

```text
LawGo Traffic
```

Python package:

```text
lawgo_traffic
```

Repository name:

```text
lawgo-traffic
```

Main GraphRAG tool name:

```text
legal_rag_search
```

---

## 12. Follow-up Specs

This spec should be used before the detailed specs:

```text
00_spec_project_scaffold.md
01_plan_build_legal_graphrag_tool.md
02_spec_legal_parser_and_chunking.md
03_spec_lightrag_indexing_and_graph_building.md
04_spec_legal_rag_search_tool.md
```

Recommended implementation order:

```text
1. Implement Spec 00: project scaffold
2. Implement Spec 02: parser and chunks
3. Implement Spec 03: LightRAG indexing and graph
4. Implement Spec 04: legal_rag_search tool
5. Connect the tool to Main Agent
```
