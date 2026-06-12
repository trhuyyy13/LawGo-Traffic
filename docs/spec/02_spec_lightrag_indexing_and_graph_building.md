# 02_SPEC — LightRAG Indexing & Legal Graph Building

> Dự án: LawGo Traffic — AI Legal Advisory Agent  
> Module: GraphRAG Indexing  
> Mục tiêu: Đưa legal chunks đã chuẩn hóa vào LightRAG để tạo semantic graph và phục vụ truy xuất căn cứ pháp lý.

---

## 1. Mục tiêu

Module này nhận đầu vào là:

```text
data/chunks/parents.jsonl
data/chunks/children.jsonl
```

Sau đó tạo ra hệ thống GraphRAG gồm:

```text
1. Structural legal graph
2. Semantic legal graph
3. Vector index
4. Metadata mapping để trace citation
```

---

## 2. Nguyên tắc thiết kế

Không đưa raw Word/PDF vào LightRAG.

Luồng đúng:

```text
Word sạch
→ Legal Parser tự build
→ Parent-child chunks
→ Feed child chunks vào LightRAG
→ Build graph
```

Lý do:

```text
- Luật Việt Nam cần giữ Điều/Khoản/Điểm chính xác.
- LightRAG mạnh ở entity/relation extraction, nhưng không nên để nó tự chunk luật.
- Citation pháp lý phải trace được về document, article, clause, point.
```

---

## 3. Graph gồm 2 lớp

### 3.1 Structural graph

Structural graph được build bằng code, không dùng LLM.

```text
Document
  └── HAS_ARTICLE → Article
        └── HAS_CLAUSE → Clause
              └── HAS_POINT → Point
```

Ví dụ:

```text
Nghị định 168/2024/NĐ-CP
  └── HAS_ARTICLE → Điều 7
        └── HAS_CLAUSE → Khoản 4
              └── HAS_POINT → Điểm a
```

### 3.2 Semantic graph

Semantic graph được extract bằng LightRAG/LLM từ child chunks.

```text
Point / Clause
  ├── REGULATES → Violation
  ├── HAS_PENALTY → Penalty
  ├── APPLIES_TO → VehicleType
  ├── HAS_CONDITION → Condition
  ├── HAS_AUTHORITY → Authority
  ├── HAS_RIGHT → Right
  └── HAS_PROCEDURE → Procedure
```

---

## 4. Node schema tối thiểu

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

Ví dụ node:

```json
{
  "node_id": "violation_vuot_den_do",
  "node_type": "Violation",
  "name": "không chấp hành hiệu lệnh của đèn tín hiệu giao thông",
  "aliases": ["vượt đèn đỏ", "không chấp hành đèn đỏ"]
}
```

---

## 5. Edge schema tối thiểu

```text
HAS_ARTICLE
HAS_CLAUSE
HAS_POINT
REGULATES
HAS_PENALTY
HAS_ADDITIONAL_PENALTY
APPLIES_TO
HAS_CONDITION
HAS_AUTHORITY
HAS_RIGHT
HAS_PROCEDURE
REFERENCES
AMENDS
REPLACES
```

Ví dụ edge:

```json
{
  "source": "nd168_2024_dieu_7_khoan_4_diem_a",
  "relation": "REGULATES",
  "target": "violation_vuot_den_do",
  "source_chunk_id": "nd168_2024_dieu_7_khoan_4_diem_a"
}
```

---

## 6. Input cho LightRAG

Dùng `children.jsonl`, nhưng truyền vào LightRAG bằng `text_for_search`, không dùng `text_raw`.

Ví dụ text đưa vào index:

```text
Nghị định 168/2024/NĐ-CP. Điều 7. Xử phạt người điều khiển xe mô tô, xe gắn máy. Khoản 4. Điểm a. Không chấp hành hiệu lệnh của đèn tín hiệu giao thông...
```

Mỗi document đưa vào LightRAG nên kèm metadata:

```json
{
  "chunk_id": "nd168_2024_dieu_7_khoan_4_diem_a",
  "parent_id": "nd168_2024_dieu_7",
  "doc_id": "nd168_2024",
  "article": "Điều 7",
  "clause": "Khoản 4",
  "point": "Điểm a"
}
```

---

## 7. Metadata mapping

Cần lưu mapping riêng để citation không phụ thuộc hoàn toàn vào LightRAG.

File:

```text
data/graph/chunk_mapping.json
```

Format:

```json
{
  "nd168_2024_dieu_7_khoan_4_diem_a": {
    "parent_id": "nd168_2024_dieu_7",
    "document_title": "Nghị định 168/2024/NĐ-CP",
    "article": "Điều 7",
    "clause": "Khoản 4",
    "point": "Điểm a",
    "source_file": "nd_168_2024.docx"
  }
}
```

---

## 8. Indexing flow

```text
1. Load children.jsonl
2. Validate mỗi chunk có chunk_id, parent_id, text_for_search
3. Build structural graph bằng code
4. Insert child chunks vào LightRAG
5. LightRAG extract entities/relations
6. Save graph artifacts
7. Save chunk_mapping.json
8. Run sanity test bằng 10 query mẫu
```

---

## 9. Query mode cần hỗ trợ

### 9.1 Local search

Dùng cho câu hỏi cụ thể:

```text
Xe máy vượt đèn đỏ phạt bao nhiêu?
```

Kỳ vọng:

```text
Violation → Penalty → Legal basis
```

### 9.2 Global search

Dùng cho câu hỏi tổng hợp:

```text
Những lỗi nào bị tước giấy phép lái xe?
```

Kỳ vọng:

```text
AdditionalPenalty contains tước GPLX → list violations
```

### 9.3 Hybrid graph search

Dùng cho câu hỏi tình huống dài:

```text
Tôi đi xe máy 125cc, vượt đèn đỏ và không đội mũ, tổng phạt bao nhiêu?
```

Kỳ vọng:

```text
Vector/BM25 tìm chunk liên quan
+ Graph tìm penalty/vehicle/condition
```

---

## 10. Sanity test

Sau indexing, chạy tối thiểu các câu:

```text
1. Xe máy vượt đèn đỏ phạt bao nhiêu?
2. Ô tô vượt đèn đỏ phạt bao nhiêu?
3. Không đội mũ bảo hiểm bị phạt bao nhiêu?
4. CSGT có quyền giữ bằng lái không?
5. Bị tạm giữ xe thì lấy lại như thế nào?
6. Những lỗi nào bị trừ điểm GPLX?
7. CSGT cấp xã phạt 10 triệu có đúng thẩm quyền không?
8. Nồng độ cồn 0.35mg/l bị phạt bao nhiêu?
9. Phạt nguội nộp ở đâu?
10. Nếu không ký biên bản thì sao?
```

Mỗi query phải trả về:

```text
- Ít nhất 1 citation
- Có document/article/clause/point nếu tìm thấy
- Có graph path nếu match được entity
```

---

## 11. Acceptance criteria

Module đạt yêu cầu khi:

```text
1. Index được toàn bộ children.jsonl vào LightRAG.
2. Structural graph có đủ Document → Article → Clause → Point.
3. Semantic graph extract được ít nhất các node Violation, Penalty, VehicleType với NĐ168.
4. Query cụ thể trả về được graph paths.
5. Mỗi result có thể map ngược về parent_id.
6. Mỗi citation trace được về document/article/clause/point.
7. Không trả result mất nguồn.
```

---

## 12. Không làm trong spec này

```text
- Không build main agent
- Không build UI
- Không voice
- Không road lookup
- Không OCR
- Không fine-tune model
```

Module này chỉ chịu trách nhiệm: **legal chunks → GraphRAG index có thể query được**.
