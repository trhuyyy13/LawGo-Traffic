# 04_SPEC — `legal_rag_search` Tool API

> Dự án: LuatGT — AI Legal Advisory Agent  
> Module: GraphRAG Tool  
> Mục tiêu: Bọc GraphRAG thành một tool riêng để Main Agent gọi khi cần căn cứ pháp lý.

---

## 1. Vai trò của tool

`legal_rag_search` không phải là chatbot hoàn chỉnh.

Tool này chỉ làm nhiệm vụ:

```text
Nhận query pháp lý
→ truy xuất GraphRAG
→ trả evidence, citations, graph paths, confidence
```

Main Agent sẽ dùng output này để tổng hợp câu trả lời cuối.

---

## 2. Vị trí trong kiến trúc

```text
User
→ Main Agent
→ legal_rag_search tool
      ├── LightRAG graph retrieval
      ├── Vector retrieval nếu cần
      ├── BM25 retrieval nếu cần
      ├── Parent context expansion
      └── Citation mapper
→ Main Agent answer
```

---

## 3. Function signature

```python
def legal_rag_search(
    query: str,
    intent: str | None = None,
    filters: dict | None = None,
    top_k: int = 5
) -> dict:
    ...
```

---

## 4. Input schema

```json
{
  "query": "Xe máy vượt đèn đỏ phạt bao nhiêu?",
  "intent": "fine_lookup",
  "filters": {
    "vehicle_type": "xe máy",
    "document_type": "nghi_dinh",
    "effective_date": "2025-01-01"
  },
  "top_k": 5
}
```

### 4.1 `intent`

Các intent ban đầu:

```text
fine_lookup
rights_lookup
authority_lookup
procedure_lookup
legal_explain
multi_violation
unknown
```

Nếu `intent = null`, tool tự detect sơ bộ hoặc dùng default hybrid mode.

### 4.2 `filters`

Filters optional:

```text
vehicle_type
violation_type
document_type
document_id
article
clause
point
effective_date
location
```

---

## 5. Output schema

```json
{
  "query": "Xe máy vượt đèn đỏ phạt bao nhiêu?",
  "intent": "fine_lookup",
  "answer_basis": [
    {
      "content": "Nội dung chunk liên quan...",
      "parent_context": "Toàn bộ Điều liên quan nếu cần...",
      "document": "Nghị định 168/2024/NĐ-CP",
      "article": "Điều ...",
      "clause": "Khoản ...",
      "point": "Điểm ...",
      "source_chunk_id": "...",
      "parent_id": "...",
      "score": 0.91
    }
  ],
  "graph_paths": [
    {
      "path": ["vượt đèn đỏ", "HAS_PENALTY", "phạt tiền ..."],
      "source_chunk_id": "..."
    }
  ],
  "matched_entities": [
    {
      "name": "vượt đèn đỏ",
      "type": "Violation",
      "confidence": 0.88
    }
  ],
  "citations": [
    {
      "document": "Nghị định 168/2024/NĐ-CP",
      "article": "Điều ...",
      "clause": "Khoản ...",
      "point": "Điểm ...",
      "source_chunk_id": "..."
    }
  ],
  "confidence": 0.86,
  "status": "ok"
}
```

---

## 6. Retrieval flow bên trong tool

```text
1. Receive query
2. Normalize query
3. Detect/confirm intent
4. Query LightRAG
5. Nếu kết quả yếu, fallback hybrid retrieval: vector + BM25
6. Merge result
7. Map child chunk → parent chunk
8. Build citations
9. Return structured evidence
```

---

## 7. Query normalization

Cần normalize các cách nói đời thường sang thuật ngữ pháp lý.

Ví dụ:

```text
vượt đèn đỏ → không chấp hành hiệu lệnh của đèn tín hiệu giao thông
xe máy → xe mô tô, xe gắn máy
bằng lái → giấy phép lái xe
giữ bằng → tước quyền sử dụng GPLX / tạm giữ GPLX
phạt nguội → xử phạt qua phương tiện, thiết bị kỹ thuật nghiệp vụ
```

Normalization không được thay thế hoàn toàn query gốc. Nên giữ cả hai:

```json
{
  "original_query": "Xe máy vượt đèn đỏ phạt bao nhiêu?",
  "normalized_query": "xe mô tô không chấp hành hiệu lệnh của đèn tín hiệu giao thông phạt tiền bao nhiêu"
}
```

---

## 8. Confidence rule

Tool trả confidence dựa trên:

```text
- Có citation rõ không
- Có graph path không
- Có match đúng vehicle/violation không
- Rerank score hoặc retrieval score
- Có parent context không
```

Gợi ý mức:

```text
>= 0.8: Có thể dùng để trả lời chắc chắn
0.5 - 0.79: Trả lời kèm lưu ý cần kiểm tra thêm
< 0.5: Không đủ căn cứ, yêu cầu hỏi rõ hơn hoặc báo không tìm thấy
```

---

## 9. Error handling

### 9.1 Không tìm thấy căn cứ

```json
{
  "answer_basis": [],
  "graph_paths": [],
  "citations": [],
  "confidence": 0.0,
  "status": "not_found",
  "message": "Không tìm thấy căn cứ pháp lý phù hợp trong corpus hiện tại."
}
```

### 9.2 Query ngoài scope

```json
{
  "status": "out_of_scope",
  "message": "Câu hỏi nằm ngoài phạm vi pháp luật giao thông đường bộ."
}
```

### 9.3 Tool lỗi nội bộ

```json
{
  "status": "error",
  "message": "GraphRAG retrieval failed.",
  "debug_id": "..."
}
```

---

## 10. Tool không được làm gì

```text
- Không tự bịa câu trả lời nếu không có citation
- Không đưa lời khuyên pháp lý vượt phạm vi corpus
- Không thay Main Agent tính toán toàn bộ multi-violation phức tạp
- Không gọi road lookup
- Không xử lý voice
```

Tool chỉ trả evidence. Agent/tools khác xử lý lập luận tiếp.

---

## 11. Test cases tối thiểu

```json
[
  {
    "query": "Xe máy vượt đèn đỏ phạt bao nhiêu?",
    "intent": "fine_lookup",
    "expected": "Có citation từ NĐ168"
  },
  {
    "query": "CSGT có được giữ bằng lái của tôi không?",
    "intent": "rights_lookup",
    "expected": "Có căn cứ về quyền/thẩm quyền hoặc tạm giữ/tước GPLX"
  },
  {
    "query": "Điều 7 Nghị định 168 nói gì?",
    "intent": "legal_explain",
    "expected": "Trả về parent context Điều 7"
  },
  {
    "query": "Tôi vừa vượt đèn đỏ vừa không đội mũ thì sao?",
    "intent": "multi_violation",
    "expected": "Trả nhiều evidence cho nhiều lỗi"
  }
]
```

---

## 12. Acceptance criteria

Tool đạt yêu cầu khi:

```text
1. Main Agent có thể gọi tool bằng JSON input.
2. Tool trả output JSON ổn định.
3. Mọi answer_basis đều có source_chunk_id.
4. Mọi citation đều trace được về document/article/clause/point nếu có.
5. Nếu không tìm thấy căn cứ, tool trả status = not_found.
6. Không trả lời chắc chắn khi confidence thấp.
7. Query mức phạt cơ bản trả được evidence trong top_k.
```

---

## 13. Không làm trong spec này

```text
- Không build UI
- Không build full agent loop
- Không fine_calculator chi tiết
- Không road intelligence
- Không voice
```

Module này chỉ chịu trách nhiệm: **GraphRAG evidence retrieval dưới dạng tool**.
