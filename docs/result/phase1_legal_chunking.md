# Phase 1 Result — Legal Parser & Parent-Child Chunking

> Dự án: LawGo Traffic
> Giai đoạn: 1 — Ingestion Pipeline
> Ngày hoàn thành: 2026-06-12
> Trạng thái: DONE — pipeline chạy end-to-end trên cả 5 file thực tế

---

## Mục tiêu giai đoạn 1

Biến 5 file Word pháp luật giao thông thành **structured legal chunks** có đầy đủ context để feed vào GraphRAG (LightRAG + Qdrant + Neo4j) ở giai đoạn sau.

---

## Những gì đã implement

### 7 files được viết mới / cập nhật hoàn chỉnh

| File | Mô tả |
|------|-------|
| `ingestion/doc_id_map.py` | DOC_ID_MAP dict + `get_doc_info()` có NFC normalization cho macOS HFS+ |
| `ingestion/id_utils.py` | `encode_point_letter()` — `đ → dd`; `make_article/clause/point_id()` stable IDs |
| `utils/text_normalizer.py` | `normalize_paragraph()` — xử lý `\xa0`, `​`, curly quotes, collapse spaces |
| `ingestion/docx_extractor.py` | `extract_docx_paragraphs()`, `extract_all_docx()` — dùng python-docx |
| `ingestion/legal_parser.py` | State machine `_LegalDocParser` với `ArticleBlock / ClauseBlock / PointBlock` |
| `ingestion/chunk_builder.py` | 4 chunk cases, `build_validation_report()`, W05 dedup tự động |
| `scripts/build_chunks.py` | Pipeline script: extracted JSON → parents.jsonl + children.jsonl |

### Pipeline hoàn chỉnh

```
data/raw/*.docx
  → (make ingest) extract_all_docx()      → data/extracted/*.json
  → (make chunks) parse + build_all_chunks → data/chunks/parents.jsonl
                                           → data/chunks/children.jsonl
                                           → data/chunks/validation_report.json
```

---

## Kết quả thực tế trên 5 file

| doc_id | File | Điều | Khoản | Điểm | Parents | Children |
|--------|------|------|-------|------|---------|----------|
| `nd168_2024` | 168.2024.NĐ.CP.docx | 55 | 332 | 910 | 55 | 1.051 |
| `luat36_2024` | 36:2024:QH15_luattrậttự.docx | 89 | 440 | 443 | 89 | 790 |
| `luat35_2024` | Luật-35-2024-QH15.docx | 86 | 388 | 383 | 86 | 670 |
| `tt24_2023_bca` | 24_2023_TT-BCA_m_559088.docx | 40 | 165 | 175 | 40 | 288 |
| `nd336_2025` | Nghị-định-336-2025-NĐ-CP.docx | 28 | 120 | 294 | 28 | 352 |
| **Tổng** | | **298** | **1.445** | **2.205** | **298** | **3.151** |

Tất cả counts khớp 100% với bảng expected trong spec01 Section 11.

### Phân loại children

| Chunk type | Ý nghĩa | Tổng |
|------------|---------|------|
| `POINT` | Điểm — có `clause_header` (mức phạt) trong `text_for_search` | 2.205 |
| `CLAUSE` | Khoản không có Điểm | 937 |
| `ARTICLE_CHILD` | Điều không có Khoản (điều khoản thi hành, v.v.) | 9 |
| **Tổng** | | **3.151** |

---

## Các vấn đề phát sinh & cách giải quyết

### 1. macOS NFD vs NFC Unicode
**Vấn đề:** macOS HFS+ lưu filename dạng NFD (decomposed). Dict key trong code dạng NFC → `get_doc_info()` không tìm thấy 3/5 file.

**Giải pháp:** `unicodedata.normalize("NFC", basename)` trước khi tra dict.

### 2. Duplicate point labels trong NĐ168
**Vấn đề:** Tài liệu gốc NĐ168 có 3 điểm bị gán nhãn trùng (lỗi của Nghị định, không phải lỗi parser):
- Điều 16 Khoản 2: hai điểm `đ)`
- Điều 40 Khoản 3: hai điểm `đ)` và hai điểm `c)`

**Giải pháp:** `_unique_chunk_id()` tự động append `_2`, `_3` cho ID trùng và log W05 kèm giải thích. Không silently overwrite.

### 3. W04 warnings — text_raw < 10 ký tự
**Vấn đề:** Một số điểm chỉ có nội dung ngắn như `"Cảnh cáo;"` (9 ký tự) hay `"Điều 11;"`.

**Đánh giá:** Đây là nội dung hợp lệ trong luật VN (điểm liệt kê tên điều/hình thức phạt). Không phải lỗi parse — giữ nguyên, không filter.

---

## Quyết định thiết kế quan trọng

### `text_for_search` bắt buộc chứa `clause_header`
Mọi POINT chunk đều có `clause_header` ("Phạt tiền từ X đến Y...") trong `text_for_search`. Lý do: nếu không có, LightRAG sẽ không biết hành vi đó bị phạt bao nhiêu khi chỉ đọc chunk của Điểm. Đây là thông tin ngữ nghĩa quan trọng nhất của NĐ168.

Ví dụ chunk Điểm a Khoản 1 Điều 6 NĐ168:
```
text_for_search:
"Nghị định 168/2024/NĐ-CP.
 Điều 6. Xử phạt, trừ điểm giấy phép lái xe của người điều khiển xe ô tô...
 Khoản 1. Phạt tiền từ 400.000 đồng đến 600.000 đồng đối với người điều khiển...
 Điểm a. [hành vi vi phạm cụ thể]"
```

### Parent-child tách biệt
- **Parent** (Article level) → dùng để mở rộng context khi Agent trả lời, không đưa vào vector search
- **Child** (Point/Clause level) → đưa vào LightRAG + Qdrant, đây là đơn vị search

### `ARTICLE_CHILD`: `chunk_id == parent_id`
Với Điều không có Khoản (ví dụ "Điều 55. Trách nhiệm thi hành"), chunk_id trỏ thẳng về parent_id để citation mapper biết đây là nội dung trực tiếp của Điều đó.

---

## Warnings summary

| Warning | Loại | Tổng | Đánh giá |
|---------|------|------|----------|
| W04 (short text_raw) | Nội dung hợp lệ ngắn | ~12 | Không cần xử lý |
| W05 (duplicate point label) | Lỗi trong tài liệu gốc | 3 | Đã tự động resolve bằng suffix |
| W01 (orphan clause) | — | 0 | Sạch |
| W02 (orphan point) | — | 0 | Sạch |
| W06 (POINT thiếu clause_header) | — | 0 | Sạch |
| W07 (ARTICLE_CHILD conflict) | — | 0 | Sạch |

---

## Output files

```
data/extracted/
  nd168_2024.json        — 1363 paragraphs
  luat36_2024.json       — 1009 paragraphs
  luat35_2024.json       —  911 paragraphs
  tt24_2023_bca.json     —  451 paragraphs
  nd336_2025.json        —  474 paragraphs

data/chunks/
  parents.jsonl          — 298 dòng (1 dòng = 1 Điều)
  children.jsonl         — 3151 dòng (1 dòng = 1 Điểm/Khoản/Điều)
  validation_report.json — report chi tiết per-file
```

---

## Giai đoạn tiếp theo (Phase 2)

Feed `children.jsonl` vào LightRAG indexing pipeline:

1. **LightRAG indexing** (`02_spec_lightrag_indexing_and_graph_building.md`)
   - Đưa `text_for_search` của từng child chunk vào LightRAG
   - LightRAG tự extract entities + relations → build semantic graph
   - Lưu vào Neo4j AuraDB + Qdrant Cloud

2. **Structural graph** — build từ `legal_path` trong mỗi chunk (không cần LLM)
   - Nodes: Document → Article → Clause → Point
   - Edges: HAS_ARTICLE, HAS_CLAUSE, HAS_POINT

3. **Qdrant indexing** — embed `text_for_search`, upsert vectors

Run: `make index`
