# 02_SPEC — Legal Parser & Parent-Child Chunking

> Dự án: LuatGT — AI Legal Advisory Agent  
> Module: Ingestion / Parser / Chunk Builder  
> Mục tiêu: Biến file Word luật giao thông sạch thành dữ liệu chunk có cấu trúc để đưa vào GraphRAG.

---

## 1. Mục tiêu

Module này nhận đầu vào là các file `.docx` hoặc `.doc` đã được convert sang `.docx`, sau đó tạo ra 2 loại dữ liệu chính:

```text
parents.jsonl
children.jsonl
```

Trong đó:

```text
Parent chunk = cấp Điều
Child chunk  = cấp Khoản hoặc Điểm
```

Child chunk dùng cho:

```text
- GraphRAG indexing
- Vector search
- BM25 search
- Entity/relation extraction
```

Parent chunk dùng cho:

```text
- Bổ sung context khi trả lời
- Citation đầy đủ
- Kiểm tra lại căn cứ pháp lý
```

---

## 2. Input

Thư mục đầu vào:

```text
data/raw/
  luat_36_2024.docx
  luat_duong_bo_2024.docx
  nd_168_2024.docx
```

Mỗi file Word được giả định là tương đối sạch:

```text
- Có text đọc được
- Không phải PDF scan
- Không cần OCR
- Cấu trúc pháp luật tương đối rõ: Chương, Mục, Điều, Khoản, Điểm
```

---

## 3. Output

### 3.1 `parents.jsonl`

Mỗi dòng là một Điều.

```json
{
  "parent_id": "nd168_2024_dieu_7",
  "doc_id": "nd168_2024",
  "chunk_type": "ARTICLE",
  "document_title": "Nghị định 168/2024/NĐ-CP",
  "chapter": "Chương II",
  "section": null,
  "article": "Điều 7",
  "article_title": "Xử phạt người điều khiển xe mô tô, xe gắn máy",
  "text": "Toàn bộ nội dung Điều 7...",
  "source_file": "nd_168_2024.docx"
}
```

### 3.2 `children.jsonl`

Mỗi dòng là một Khoản hoặc Điểm.

```json
{
  "chunk_id": "nd168_2024_dieu_7_khoan_4_diem_a",
  "parent_id": "nd168_2024_dieu_7",
  "doc_id": "nd168_2024",
  "chunk_type": "POINT",
  "text_raw": "Không chấp hành hiệu lệnh của đèn tín hiệu giao thông...",
  "text_for_search": "Nghị định 168/2024/NĐ-CP. Điều 7. Xử phạt người điều khiển xe mô tô, xe gắn máy. Khoản 4. Điểm a. Không chấp hành hiệu lệnh của đèn tín hiệu giao thông...",
  "legal_path": {
    "document_title": "Nghị định 168/2024/NĐ-CP",
    "chapter": "Chương II",
    "section": null,
    "article": "Điều 7",
    "article_title": "Xử phạt người điều khiển xe mô tô, xe gắn máy",
    "clause": "Khoản 4",
    "point": "Điểm a"
  },
  "source_file": "nd_168_2024.docx"
}
```

---

## 4. Parsing rule

### 4.1 Nhận diện cấu trúc

Regex cơ bản:

```python
CHAPTER_PATTERN = r"^Chương\s+[IVXLCDM]+"
SECTION_PATTERN = r"^Mục\s+\d+"
ARTICLE_PATTERN = r"^Điều\s+\d+[a-zA-Z]?\."
CLAUSE_PATTERN = r"^\d+\."
POINT_PATTERN = r"^[a-zđ]\)"
```

### 4.2 Luồng parser

```text
Đọc từng paragraph
→ Nếu gặp Chương: cập nhật current_chapter
→ Nếu gặp Mục: cập nhật current_section
→ Nếu gặp Điều: tạo article mới
→ Nếu gặp Khoản: gán vào article hiện tại
→ Nếu gặp Điểm: gán vào khoản hiện tại
→ Nếu không match: nối tiếp vào block hiện tại
```

### 4.3 Quy tắc chunk

```text
Nếu Điều có các Khoản:
  - Parent = toàn bộ Điều
  - Child = từng Khoản

Nếu Khoản có các Điểm:
  - Parent = toàn bộ Điều
  - Child = từng Điểm

Nếu Điều ngắn không có Khoản:
  - Parent = Điều
  - Child = Điều đó, chunk_type = ARTICLE_CHILD
```

---

## 5. ID convention

ID cần ổn định, dễ debug, không dùng UUID ngẫu nhiên.

Format:

```text
{doc_id}_dieu_{article_number}
{doc_id}_dieu_{article_number}_khoan_{clause_number}
{doc_id}_dieu_{article_number}_khoan_{clause_number}_diem_{point_letter}
```

Ví dụ:

```text
nd168_2024_dieu_7
nd168_2024_dieu_7_khoan_4
nd168_2024_dieu_7_khoan_4_diem_a
```

---

## 6. Làm sạch text

### 6.1 Được xóa

```text
- Dòng trống thừa
- Header/footer lặp
- Số trang
- Ký tự lỗi encoding
- Mục lục nếu có
```

### 6.2 Không được xóa

```text
- Số Điều
- Số Khoản
- Điểm a), b), c)
- Tên văn bản
- Tên Chương/Mục
- Mức tiền phạt
- Ngày hiệu lực
```

---

## 7. Validation bắt buộc

Sau khi parse xong, cần in report:

```json
{
  "source_file": "nd_168_2024.docx",
  "total_articles": 75,
  "total_clauses": 420,
  "total_points": 900,
  "parents_count": 75,
  "children_count": 900,
  "warnings": []
}
```

Cảnh báo nếu:

```text
- Có Khoản không thuộc Điều nào
- Có Điểm không thuộc Khoản nào
- Có Điều không tạo được parent_id
- Có child chunk text quá ngắn
- Có duplicate chunk_id
```

---

## 8. Acceptance criteria

Module đạt yêu cầu khi:

```text
1. Parse được ít nhất 3 văn bản chính: Luật 36/2024, Luật Đường bộ 2024, NĐ168/2024.
2. Sinh được parents.jsonl và children.jsonl hợp lệ.
3. Mỗi child chunk đều có parent_id.
4. Mỗi child chunk đều có legal_path đầy đủ.
5. text_for_search có code-on tên văn bản + Điều/Khoản/Điểm.
6. Không có duplicate chunk_id.
7. Kiểm tra thủ công 20 chunk thấy không mất căn cứ pháp lý.
```

---

## 9. Không làm trong spec này

```text
- Không gọi LLM
- Không build LightRAG
- Không build vector DB
- Không trả lời user
- Không OCR/PDF scan
```

Module này chỉ chịu trách nhiệm: **Word sạch → structured legal chunks**.
