# 01_plan_build_legal_graphrag_tool.md

# Plan xây dựng Legal GraphRAG Tool cho LuatGT

## 1. Mục tiêu

Xây dựng một **GraphRAG tool** phục vụ Agent chính của LuatGT.

Tool này không phải chatbot độc lập. Nó là một công cụ để Agent gọi khi cần tra cứu căn cứ pháp lý, ví dụ:

- Mức phạt giao thông
- Quyền của người bị dừng xe
- Thẩm quyền xử phạt
- Thủ tục nộp phạt, lấy lại xe, khiếu nại
- Cross-reference giữa Luật, Nghị định, Thông tư

Luồng tổng thể:

```text
User
→ Main Agent
→ gọi legal_rag_search tool khi cần căn cứ pháp lý
→ GraphRAG trả evidence + citation + graph paths
→ Main Agent tổng hợp câu trả lời cuối
```

---

## 2. Định hướng chính

Hệ thống sẽ dùng hướng:

```text
Legal Parser tự build
+ Legal Parent-Child Chunking tự build
+ Structural Legal Graph tự build
+ LightRAG làm graph engine / semantic graph retrieval
+ legal_rag_search làm tool cho Agent
```

Không làm theo kiểu:

```text
Raw Word/PDF → LightRAG tự chunk → tự hiểu luật
```

Lý do: văn bản pháp luật Việt Nam có cấu trúc rất chặt như Điều, Khoản, Điểm. Nếu để framework tự chunk theo token, hệ thống dễ mất căn cứ pháp lý và citation sai.

---

## 3. Phạm vi v1

### Làm trong v1

- Xử lý file Word sạch: `.docx`, hoặc `.doc` đã convert sang `.docx`
- Extract text từ Word
- Parse cấu trúc pháp luật:
  - Văn bản
  - Chương
  - Mục
  - Điều
  - Khoản
  - Điểm
- Tạo parent-child chunks
- Build structural graph:
  - Document → Article → Clause → Point
- Đưa child chunks vào LightRAG
- Tạo tool `legal_rag_search`
- Test bằng một số câu hỏi về luật giao thông

### Chưa làm trong v1

- OCR / PDF scan / Vision-based parsing
- Voice STT/TTS
- Road intelligence / Overpass API
- Fine-tune embedding/reranker
- Neo4j production graph
- Full UI chatbot
- B2B API

---

## 4. Kiến trúc tổng quan

```text
Word legal documents
    ↓
Extract text
    ↓
Legal parser
    ↓
Parent-child chunks
    ↓
Structural graph builder
    ↓
LightRAG indexing
    ↓
legal_rag_search tool
    ↓
Main Agent
```

Trong đó:

```text
Parent chunk = toàn bộ Điều
Child chunk = Khoản hoặc Điểm
```

Child chunk dùng để:

- Search
- Embedding
- BM25 nếu cần
- Entity/relation extraction
- Build semantic graph

Parent chunk dùng để:

- Mở rộng context
- Đưa cho LLM đọc khi trả lời
- Giữ citation đầy đủ

---

## 5. Thứ tự triển khai

## Step 1 — Chuẩn bị repository

Tạo cấu trúc thư mục ban đầu:

```text
luatgt-graphrag/
├── data/
│   ├── raw/
│   ├── extracted/
│   ├── parsed/
│   ├── chunks/
│   └── graph/
│
├── src/
│   ├── ingestion/
│   ├── graph/
│   ├── rag/
│   ├── tools/
│   └── eval/
│
├── tests/
├── scripts/
├── README.md
└── requirements.txt
```

Deliverable:

```text
Repo skeleton chạy được.
```

---

## Step 2 — Extract text từ Word

Input:

```text
data/raw/*.docx
```

Output:

```text
data/extracted/*.json
```

Mỗi file JSON nên chứa:

```json
{
  "doc_id": "nd168_2024",
  "title": "Nghị định 168/2024/NĐ-CP",
  "source_file": "nd168_2024.docx",
  "raw_text": "..."
}
```

Việc cần làm:

- Đọc `.docx` bằng `python-docx`
- Giữ nguyên thứ tự đoạn văn
- Loại dòng trống thừa
- Chưa cần xử lý OCR/PDF

Deliverable:

```text
extract_docx.py
```

---

## Step 3 — Viết Legal Parser

Parser cần tách được cấu trúc:

```text
Document
→ Chapter
→ Section
→ Article
→ Clause
→ Point
```

Regex gợi ý:

```python
CHAPTER_PATTERN = r"^Chương\s+[IVXLCDM]+"
SECTION_PATTERN = r"^Mục\s+\d+"
ARTICLE_PATTERN = r"^Điều\s+\d+[a-zA-Z]?\."
CLAUSE_PATTERN = r"^\d+\."
POINT_PATTERN = r"^[a-zđ]\)"
```

Output:

```text
data/parsed/*.json
```

Mỗi đơn vị parse nên có thông tin:

```json
{
  "doc_id": "nd168_2024",
  "chapter": "Chương II",
  "section": "Mục 1",
  "article": "Điều 7",
  "article_title": "Xử phạt người điều khiển xe mô tô, xe gắn máy",
  "clause": "Khoản 4",
  "point": "Điểm a",
  "text": "..."
}
```

Deliverable:

```text
legal_parser.py
```

Tiêu chí đạt:

```text
Parse đúng ít nhất 90% Điều/Khoản/Điểm trong 1 văn bản mẫu.
```

---

## Step 4 — Build parent-child chunks

Tạo 2 loại chunk.

### 4.1 Parent chunks

Parent chunk là toàn bộ một Điều.

Output:

```text
data/chunks/parents.jsonl
```

Ví dụ:

```json
{
  "parent_id": "nd168_2024_dieu_7",
  "doc_id": "nd168_2024",
  "chunk_type": "ARTICLE",
  "article": "Điều 7",
  "article_title": "Xử phạt người điều khiển xe mô tô, xe gắn máy",
  "text": "Toàn bộ Điều 7..."
}
```

### 4.2 Child chunks

Child chunk là Khoản hoặc Điểm.

Output:

```text
data/chunks/children.jsonl
```

Ví dụ:

```json
{
  "chunk_id": "nd168_2024_dieu_7_khoan_4_diem_a",
  "parent_id": "nd168_2024_dieu_7",
  "doc_id": "nd168_2024",
  "chunk_type": "POINT",
  "text_raw": "Không chấp hành hiệu lệnh của đèn tín hiệu giao thông...",
  "text_for_search": "Nghị định 168/2024/NĐ-CP. Điều 7. Xử phạt người điều khiển xe mô tô, xe gắn máy. Khoản 4. Điểm a. Không chấp hành hiệu lệnh của đèn tín hiệu giao thông...",
  "metadata": {
    "document": "Nghị định 168/2024/NĐ-CP",
    "article": "Điều 7",
    "clause": "Khoản 4",
    "point": "Điểm a"
  }
}
```

Deliverable:

```text
chunk_builder.py
parents.jsonl
children.jsonl
```

---

## Step 5 — Build structural legal graph

Trước khi dùng LightRAG, tự build graph cấu trúc pháp lý bằng code.

Graph tối thiểu:

```text
Document → HAS_ARTICLE → Article
Article → HAS_CLAUSE → Clause
Clause → HAS_POINT → Point
```

Output:

```text
data/graph/structural_graph.jsonl
```

Ví dụ:

```json
{"source": "nd168_2024", "relation": "HAS_ARTICLE", "target": "nd168_2024_dieu_7"}
{"source": "nd168_2024_dieu_7", "relation": "HAS_CLAUSE", "target": "nd168_2024_dieu_7_khoan_4"}
{"source": "nd168_2024_dieu_7_khoan_4", "relation": "HAS_POINT", "target": "nd168_2024_dieu_7_khoan_4_diem_a"}
```

Deliverable:

```text
structural_graph_builder.py
```

---

## Step 6 — Index vào LightRAG

Input chính cho LightRAG:

```text
data/chunks/children.jsonl
```

Không index raw Word trực tiếp.

Mỗi child chunk đưa vào LightRAG phải có legal path ở đầu text:

```text
Nghị định 168/2024/NĐ-CP.
Điều 7. Xử phạt người điều khiển xe mô tô, xe gắn máy.
Khoản 4.
Điểm a.
Nội dung quy định...
```

LightRAG dùng để:

- Extract semantic entities
- Extract relations
- Build semantic graph
- Graph retrieval
- Hỗ trợ multi-hop query

Deliverable:

```text
lightrag_indexer.py
```

---

## Step 7 — Thiết kế semantic graph mục tiêu

Semantic graph cần hướng tới các node/edge sau.

### Node types

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

### Edge types

```text
HAS_ARTICLE
HAS_CLAUSE
HAS_POINT
REGULATES
HAS_PENALTY
APPLIES_TO
HAS_AUTHORITY
HAS_RIGHT
HAS_PROCEDURE
HAS_CONDITION
REFERENCES
AMENDS
REPLACES
```

Ví dụ mong muốn:

```text
Điểm a Khoản 4 Điều 7
→ REGULATES → vượt đèn đỏ
vượt đèn đỏ
→ APPLIES_TO → xe mô tô
vượt đèn đỏ
→ HAS_PENALTY → phạt tiền ...
```

Deliverable:

```text
graph_schema.py
```

---

## Step 8 — Build `legal_rag_search` tool

Đây là tool mà Main Agent sẽ gọi.

Input:

```json
{
  "query": "Xe máy vượt đèn đỏ phạt bao nhiêu?",
  "intent": "fine_lookup",
  "filters": {
    "vehicle_type": "xe máy"
  }
}
```

Output:

```json
{
  "evidence": [
    {
      "content": "...",
      "document": "Nghị định 168/2024/NĐ-CP",
      "article": "Điều ...",
      "clause": "Khoản ...",
      "point": "Điểm ...",
      "chunk_id": "...",
      "parent_id": "..."
    }
  ],
  "graph_paths": [
    "vượt đèn đỏ -> APPLIES_TO -> xe mô tô",
    "vượt đèn đỏ -> HAS_PENALTY -> phạt tiền ..."
  ],
  "confidence": 0.85
}
```

Tool không cần trả lời văn phong cuối cùng. Tool chỉ trả căn cứ.

Deliverable:

```text
legal_rag_search.py
```

---

## Step 9 — Tích hợp với Main Agent

Main Agent có nhiệm vụ:

```text
1. Nhận câu hỏi user
2. Phân loại intent
3. Gọi legal_rag_search nếu cần căn cứ luật
4. Có thể gọi thêm fine_calculator / rights_checker / authority_checker
5. Tổng hợp câu trả lời cuối
```

Luồng:

```text
User hỏi
→ Main Agent
→ legal_rag_search
→ evidence + graph_paths
→ Main Agent trả lời có citation
```

Deliverable:

```text
agent_orchestrator.py hoặc LangGraph node
```

---

## Step 10 — Test và evaluation

Tạo bộ test ban đầu khoảng 30–50 câu.

Nhóm câu hỏi:

```text
1. Hỏi mức phạt trực tiếp
2. Hỏi nhiều lỗi cùng lúc
3. Hỏi quyền khi bị CSGT dừng xe
4. Hỏi thẩm quyền xử phạt
5. Hỏi thủ tục nộp phạt / lấy lại xe
6. Hỏi câu không có trong corpus
```

Metrics tối thiểu:

```text
- Retrieval hit rate
- Citation accuracy
- Context relevance
- Faithfulness
- Answer correctness manual check
```

Deliverable:

```text
golden_questions.json
eval_report.md
```

---

## 6. Milestones đề xuất

## Milestone 1 — Parser chạy được

Output:

```text
extracted JSON
parsed JSON
```

Kết quả mong muốn:

```text
Nhìn được cây Document → Điều → Khoản → Điểm.
```

---

## Milestone 2 — Chunk đúng

Output:

```text
parents.jsonl
children.jsonl
```

Kết quả mong muốn:

```text
Mỗi child chunk có parent_id và legal_path đầy đủ.
```

---

## Milestone 3 — LightRAG index được

Output:

```text
LightRAG storage/index
```

Kết quả mong muốn:

```text
Query thử trả ra được chunk liên quan.
```

---

## Milestone 4 — legal_rag_search chạy được

Output:

```text
legal_rag_search(query) → evidence + citation + graph_paths
```

Kết quả mong muốn:

```text
Tool trả căn cứ pháp lý đủ để Agent tổng hợp câu trả lời.
```

---

## Milestone 5 — Agent gọi được GraphRAG tool

Output:

```text
Main Agent → legal_rag_search → final answer
```

Kết quả mong muốn:

```text
Người dùng hỏi tự nhiên, Agent trả lời có căn cứ.
```

---

## 7. Stack đề xuất cho v1

```text
Language: Python
Doc extraction: python-docx
Parser: regex + custom parser
GraphRAG: LightRAG
Vector: LightRAG built-in trước, Qdrant sau nếu cần
Graph store: LightRAG local/NetworkX trước, Neo4j sau nếu cần
Metadata store: JSONL trước, PostgreSQL sau
API: FastAPI
Agent orchestration: LangGraph hoặc tự viết router đơn giản
Eval: custom golden set + RAGAS sau
```

---

## 8. Nguyên tắc quan trọng

1. Không để LightRAG tự chunk raw document.
2. Luôn giữ legal path trong mỗi child chunk.
3. Search trên child chunk, trả lời bằng parent context.
4. Graph có 2 lớp:
   - Structural graph: build bằng code
   - Semantic graph: LightRAG/LLM extract
5. Tool GraphRAG không trả lời cuối, chỉ trả evidence.
6. Agent chính mới là nơi tổng hợp câu trả lời.
7. Không có citation thì không trả lời chắc chắn.

---

## 9. Việc làm đầu tiên ngay sau file plan này

Bắt đầu bằng 3 file code:

```text
src/ingestion/extract_docx.py
src/ingestion/legal_parser.py
src/ingestion/chunk_builder.py
```

Mục tiêu đầu tiên:

```text
Từ 1 file Word sạch
→ sinh được parents.jsonl và children.jsonl chuẩn.
```

Khi có 2 file này, mới bắt đầu index LightRAG.

