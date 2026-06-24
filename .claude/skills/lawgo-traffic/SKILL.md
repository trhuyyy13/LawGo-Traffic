---
name: lawgo-traffic
description: |-
  Project context skill for LawGo Traffic — AI Legal Advisory Agent for Vietnam Traffic Law.
  TRIGGER whenever: working on any file inside this project; user mentions LawGo, LawGo Traffic, luật giao thông, legal RAG, GraphRAG, LightRAG, legal parser, chunk, legal_rag_search, main agent, intent router, fine calculator, rights checker, voice STT/TTS, Supabase, Qdrant, Neo4j AuraDB in the context of this project; user asks about architecture, module structure, tech stack, or data pipeline of this project.
  SKIP when the user is explicitly working on a different, unrelated project.
---

# LawGo Traffic — Project Skill

Load this skill to have full context about the LawGo Traffic project before writing any code, answer, or suggestion.

---

## 1. Product Identity

- **Name:** LawGo Traffic
- **Tagline:** AI Legal Advisory Agent for Vietnam Traffic Law
- **Python package:** `lawgo_traffic`
- **Repo name:** `lawgo-traffic`
- **Core tool name:** `legal_rag_search`

---

## 2. Product Vision

LawGo Traffic is **not** a plain RAG chatbot. It is a **ReAct Agent + Tool-based GraphRAG** system.

User inputs a **voice or text** description of a traffic situation (e.g., "Tôi vừa bị CSGT dừng xe vì vượt đèn đỏ, họ đòi giữ bằng..."). The Main Agent:

1. Classifies intent
2. Thinks (reasoning step)
3. Calls the right tools autonomously
4. Synthesizes a final answer **always with legal citations** (văn bản, điều, khoản, điểm)

**Core principle:** No citation → no confident answer. Agent must not fabricate legal provisions.

---

## 3. Architecture

```
User (voice / text)
  ↓
STTAdapter (nếu voice)
  ↓
Main Agent — LangGraph ReAct loop
  ├── legal_rag_search   ← PRIMARY tool — LightRAG + Qdrant + Neo4j
  ├── fine_calculator    ← tính mức phạt, multi-violation
  ├── rights_checker     ← quyền người tham gia giao thông
  ├── authority_checker  ← thẩm quyền xử phạt (NĐ168 Điều 70-72)
  └── procedure_lookup   ← nộp phạt, lấy xe, khiếu nại
  ↓
Final answer + citations (Điều/Khoản/Điểm)
  ↓
TTSAdapter (nếu voice response)
```

`legal_rag_search` chỉ trả **evidence + citations + graph_paths**, không trả câu trả lời cuối. Agent mới tổng hợp.

---

## 4. Tech Stack

| Layer | Tech |
|-------|------|
| Backend API | FastAPI (`src/lawgo_traffic/api/`) |
| UI | Streamlit (`ui/`) |
| Agent loop | LangGraph ReAct |
| GraphRAG engine | LightRAG |
| Vector DB | Qdrant Cloud |
| Graph DB | Neo4j AuraDB Free |
| Relational / File storage | Supabase PostgreSQL + Storage |
| Cache / Session | Redis |
| Container | Docker Compose (api :8080, ui :8501, redis :6379) |
| Doc parsing | python-docx + regex |
| Search | BM25s (keyword fallback) |
| Voice STT | PhoWhisper (VinAI) — gated by `VOICE_ENABLED=true` |
| Voice TTS | Edge-TTS `vi-VN-HoaiMyNeural` — gated by `VOICE_ENABLED=true` |

---

## 5. Module Map (`src/lawgo_traffic/`)

```
config.py           — pydantic-settings, all env vars
api/
  main.py           — FastAPI app, mounts routers
  schemas.py        — Pydantic request/response models
  routes_chat.py    — POST /chat, POST /tools/legal-rag-search
agent/
  main_agent.py     — MainAgent class, ReAct loop (LangGraph)
  intent_router.py  — detect_intent(), intent constants
  prompts.py        — SYSTEM_PROMPT
ingestion/
  docx_extractor.py — extract_docx_to_text(), extract_all_docx()
  legal_parser.py   — parse_legal_document() → list[LegalUnit]
  chunk_builder.py  — build_parent_chunks(), build_child_chunks()
  id_utils.py       — make_article_id(), make_clause_id(), make_point_id()
graph/
  schema.py         — NodeType, EdgeType enums
  structural_graph_builder.py — rule-based, no LLM
  semantic_graph_builder.py   — LightRAG/LLM entity extraction
  graph_store.py    — Neo4j AuraDB adapter
rag/
  lightrag_adapter.py  — LightRAGAdapter (wraps LightRAG)
  vector_retriever.py  — VectorRetriever (Qdrant Cloud)
  bm25_retriever.py    — BM25Retriever (keyword fallback)
  citation_mapper.py   — chunk_id → citation dict
  result_types.py      — LegalRAGSearchResult, AnswerBasis dataclasses
  legal_rag_search.py  — legal_rag_search() — THE core tool
tools/
  fine_calculator.py   — calculate_fine(violations)
  rights_checker.py    — check_rights(situation)
  authority_checker.py — check_authority(officer_type, fine_amount)
  procedure_lookup.py  — lookup_procedure(procedure_type)
voice/
  stt_adapter.py    — STTAdapter.transcribe(audio_bytes)
  tts_adapter.py    — TTSAdapter.synthesize(text)
eval/
  metrics.py        — retrieval_hit_rate, citation_accuracy, context_relevance
  evaluator.py      — run_evaluation(questions_path)
utils/
  jsonl.py          — load_jsonl(), save_jsonl()
  text_normalizer.py — normalize_whitespace(), normalize_legal_terms()
```

---

## 6. Data Layer

### Directory layout
```
data/
  raw/        — Original .docx legal documents (DO NOT modify)
  extracted/  — Text-extracted JSON from docx
  parsed/     — LegalUnit JSON per document
  chunks/
    parents.jsonl   — Article-level chunks
    children.jsonl  — Clause/Point-level chunks (fed into LightRAG)
  graph/
    lightrag/       — LightRAG working dir
    chunk_mapping.json  — chunk_id → citation metadata
  eval/
    golden_questions.sample.json
```

### Raw legal documents (data/raw/)
- `168.2024.NĐ.CP.docx` — Nghị định 168/2024/NĐ-CP (mức phạt mới)
- `36:2024:QH15_luattrậttự.docx` — Luật Trật tự ATGT Đường bộ 36/2024/QH15
- `Luật-35-2024-QH15.docx` — Luật Đường bộ 35/2024/QH15
- `24_2023_TT-BCA_m_559088.docx` — Thông tư 24/2023/TT-BCA
- `Nghị-định-336-2025-NĐ-CP.docx` — Nghị định 336/2025/NĐ-CP

### Key data formats

**Parent chunk** (Article level):
```json
{
  "parent_id": "nd168_2024_dieu_7",
  "doc_id": "nd168_2024",
  "chunk_type": "ARTICLE",
  "document_title": "Nghị định 168/2024/NĐ-CP",
  "article": "Điều 7",
  "article_title": "Xử phạt người điều khiển xe mô tô...",
  "text": "Toàn bộ nội dung Điều 7..."
}
```

**Child chunk** (Clause/Point level — input to LightRAG):
```json
{
  "chunk_id": "nd168_2024_dieu_7_khoan_4_diem_a",
  "parent_id": "nd168_2024_dieu_7",
  "chunk_type": "POINT",
  "text_for_search": "Nghị định 168/2024/NĐ-CP. Điều 7. Khoản 4. Điểm a. Không chấp hành hiệu lệnh...",
  "legal_path": { "document_title": "...", "article": "Điều 7", "clause": "Khoản 4", "point": "Điểm a" }
}
```

### ID convention
```
{doc_id}_dieu_{n}
{doc_id}_dieu_{n}_khoan_{k}
{doc_id}_dieu_{n}_khoan_{k}_diem_{letter}
```

---

## 7. Data Pipeline (scripts/)

```bash
make ingest   # python scripts/ingest_docx.py   — raw docx → extracted JSON
make chunks   # python scripts/build_chunks.py  — extracted → parents + children JSONL
make index    # python scripts/build_graph_index.py — children → LightRAG + Neo4j + Qdrant
make eval     # python scripts/run_eval.py       — golden questions evaluation
```

---

## 8. API Endpoints

```
GET  /health                    — service health
POST /chat                      — user message (text or base64 audio) → agent answer
POST /tools/legal-rag-search    — direct tool call → evidence + citations
```

`POST /chat` request:
```json
{ "message": "...", "audio": null, "session_id": "optional" }
```

`POST /tools/legal-rag-search` request:
```json
{ "query": "...", "intent": "fine_lookup", "filters": {}, "top_k": 5 }
```

---

## 9. Intent Types

```
fine_lookup        — mức phạt cụ thể
multi_violation    — nhiều lỗi cùng lúc
rights_lookup      — quyền khi bị dừng xe
authority_lookup   — thẩm quyền xử phạt
procedure_lookup   — nộp phạt, lấy xe, khiếu nại
legal_explain      — giải thích điều khoản cụ thể
out_of_scope       — ngoài phạm vi
unknown            — chưa xác định
```

---

## 10. Graph Schema

**Node types:** `Document, Article, Clause, Point, Violation, Penalty, VehicleType, Authority, Right, Procedure, Condition, LegalConcept`

**Edge types:** `HAS_ARTICLE, HAS_CLAUSE, HAS_POINT, REGULATES, HAS_PENALTY, HAS_ADDITIONAL_PENALTY, APPLIES_TO, HAS_CONDITION, HAS_AUTHORITY, HAS_RIGHT, HAS_PROCEDURE, REFERENCES, AMENDS, REPLACES`

Two graph layers:
- **Structural graph** — built by code, no LLM (Document → Article → Clause → Point)
- **Semantic graph** — extracted by LightRAG/LLM from child chunks

---

## 11. Current State

**Scaffold only — all modules are stubs (`raise NotImplementedError`).**

Implemented so far:
- Full directory structure + Docker Compose
- FastAPI skeleton (health + chat + legal-rag-search endpoints return stubs)
- All module interfaces, class signatures, function signatures
- `utils/jsonl.py` and `utils/text_normalizer.py` are implemented
- `id_utils.py` is implemented
- `graph/schema.py` NodeType/EdgeType enums are complete
- `config.py` is complete

Not yet implemented:
- `docx_extractor.py` — needs python-docx logic
- `legal_parser.py` — needs regex state machine
- `chunk_builder.py` — needs chunking logic
- `structural_graph_builder.py` / `semantic_graph_builder.py` — needs graph building
- `lightrag_adapter.py` — needs LightRAG init + query
- `vector_retriever.py` — needs Qdrant client
- `legal_rag_search.py` — needs full retrieval pipeline
- `main_agent.py` — needs LangGraph ReAct loop
- All tools (`fine_calculator`, `rights_checker`, etc.)
- Voice adapters

---

## 12. Core Principles

1. **No citation → no confident answer.** Never fabricate điều/khoản/điểm.
2. **Never let LightRAG self-chunk raw Word files.** Always pre-process: docx → parser → parent/child chunks → LightRAG.
3. **Child chunk for search, parent chunk for context.** Search on children, expand to parent before answering.
4. **legal_rag_search returns evidence only.** Agent synthesizes the final answer.
5. **Voice is gated by `VOICE_ENABLED=true`.** Never import voice deps when flag is false.
6. **Docker for everything.** No local runtime assumptions — run via `make up`.
7. **Confidence < 0.5 → do not answer confidently.** Return `status: not_found` or ask user to clarify.
