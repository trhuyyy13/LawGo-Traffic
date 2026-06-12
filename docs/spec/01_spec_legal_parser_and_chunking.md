# 01_SPEC — Legal Parser & Parent-Child Chunking

> Dự án: LawGo Traffic — AI Legal Advisory Agent
> Module: Ingestion / Parser / Chunk Builder
> Mục tiêu: Biến file Word luật giao thông sạch thành dữ liệu chunk có cấu trúc để đưa vào GraphRAG.
> Phiên bản: 1.1 — cập nhật sau khi phân tích thực tế 5 file docx.

---

## 1. Mục tiêu

Module này nhận đầu vào là các file `.docx`, sau đó tạo ra 2 loại dữ liệu chính:

```text
parents.jsonl
children.jsonl
```

Trong đó:

```text
Parent chunk = cấp Điều
Child chunk  = cấp Điểm (ưu tiên) hoặc Khoản (nếu không có Điểm)
```

Child chunk dùng cho:

```text
- GraphRAG indexing (feed vào LightRAG)
- Vector search (Qdrant)
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

## 2. Input — Danh sách file thực tế

### 2.1 Files trong `data/raw/`

| filename | doc_id | document_title | Loại | Điều | Khoản | Điểm |
|----------|--------|----------------|------|------|-------|------|
| `168.2024.NĐ.CP.docx` | `nd168_2024` | Nghị định 168/2024/NĐ-CP | Nghị định | 55 | 332 | 910 |
| `36:2024:QH15_luattrậttự.docx` | `luat36_2024` | Luật 36/2024/QH15 | Luật | 89 | 440 | 443 |
| `Luật-35-2024-QH15.docx` | `luat35_2024` | Luật 35/2024/QH15 | Luật | 86 | 388 | 383 |
| `24_2023_TT-BCA_m_559088.docx` | `tt24_2023_bca` | Thông tư 24/2023/TT-BCA | Thông tư | 40 | 165 | 175 |
| `Nghị-định-336-2025-NĐ-CP.docx` | `nd336_2025` | Nghị định 336/2025/NĐ-CP | Nghị định | 28 | 120 | 294 |

Mapping này phải được lưu trong `src/lawgo_traffic/ingestion/doc_id_map.py` dưới dạng dict constant. Không hardcode string trong parser.

### 2.2 Giả định về chất lượng file

```text
- Có text đọc được, không phải PDF scan
- Không cần OCR
- Không có mục lục (TOC) — đã xác nhận qua phân tích thực tế
- Không có sub-point lồng nhau kiểu a1), b2) — đã xác nhận
- Article title LUÔN nằm trên cùng dòng với "Điều N." — đã xác nhận
- Clause numbers có space sau dấu chấm — đã xác nhận
- Clause numbers cao nhất là 14 (Điều 6 NĐ168) — regex giới hạn 1-2 chữ số là đủ
```

---

## 3. Output

### 3.1 `parents.jsonl`

Mỗi dòng là một Điều. Dùng để mở rộng context khi Agent trả lời.

```json
{
  "parent_id": "nd168_2024_dieu_7",
  "doc_id": "nd168_2024",
  "chunk_type": "ARTICLE",
  "document_title": "Nghị định 168/2024/NĐ-CP",
  "chapter": "Chương II",
  "chapter_title": "HÀNH VI VI PHẠM, HÌNH THỨC, MỨC XỬ PHẠT...",
  "section": "Mục 1",
  "section_title": "VI PHẠM QUY TẮC GIAO THÔNG ĐƯỜNG BỘ",
  "article": "Điều 7",
  "article_title": "Xử phạt, trừ điểm giấy phép lái của người điều khiển xe mô tô...",
  "text": "Toàn bộ nội dung Điều 7 ghép từ tất cả các paragraph...",
  "source_file": "168.2024.NĐ.CP.docx"
}
```

**Lưu ý:** `chapter_title` và `section_title` là paragraph tiếp theo sau `Chương X` / `Mục X` (xem Gap 1 bên dưới). `section` và `section_title` là `null` nếu văn bản không có Mục (ví dụ Luật 36 không có Mục).

### 3.2 `children.jsonl`

Mỗi dòng là một Điểm hoặc Khoản (tùy cấu trúc Điều).

**Case A — child là Điểm** (`chunk_type: "POINT"`):

```json
{
  "chunk_id": "nd168_2024_dieu_7_khoan_1_diem_a",
  "parent_id": "nd168_2024_dieu_7",
  "doc_id": "nd168_2024",
  "chunk_type": "POINT",
  "text_raw": "Không chấp hành hiệu lệnh, chỉ dẫn của biển báo hiệu, vạch kẻ đường...",
  "clause_header": "Phạt tiền từ 200.000 đồng đến 400.000 đồng đối với người điều khiển xe thực hiện một trong các hành vi vi phạm sau đây:",
  "text_for_search": "Nghị định 168/2024/NĐ-CP. Điều 7. Xử phạt, trừ điểm giấy phép lái của người điều khiển xe mô tô... Khoản 1. Phạt tiền từ 200.000 đồng đến 400.000 đồng đối với người điều khiển xe thực hiện một trong các hành vi vi phạm sau đây: Điểm a. Không chấp hành hiệu lệnh, chỉ dẫn của biển báo hiệu, vạch kẻ đường...",
  "legal_path": {
    "document_title": "Nghị định 168/2024/NĐ-CP",
    "chapter": "Chương II",
    "chapter_title": "HÀNH VI VI PHẠM...",
    "section": "Mục 1",
    "section_title": "VI PHẠM QUY TẮC GIAO THÔNG ĐƯỜNG BỘ",
    "article": "Điều 7",
    "article_title": "Xử phạt, trừ điểm giấy phép lái của người điều khiển xe mô tô...",
    "clause": "Khoản 1",
    "clause_header": "Phạt tiền từ 200.000 đồng đến 400.000 đồng...",
    "point": "Điểm a"
  },
  "source_file": "168.2024.NĐ.CP.docx"
}
```

**Case B — child là Khoản không có Điểm** (`chunk_type: "CLAUSE"`):

```json
{
  "chunk_id": "nd168_2024_dieu_1_khoan_1",
  "parent_id": "nd168_2024_dieu_1",
  "doc_id": "nd168_2024",
  "chunk_type": "CLAUSE",
  "text_raw": "Nghị định này quy định về: xử phạt vi phạm hành chính...",
  "clause_header": null,
  "text_for_search": "Nghị định 168/2024/NĐ-CP. Điều 1. Phạm vi điều chỉnh. Khoản 1. Nghị định này quy định về: xử phạt vi phạm hành chính...",
  "legal_path": {
    "document_title": "Nghị định 168/2024/NĐ-CP",
    "chapter": "Chương I",
    "chapter_title": "NHỮNG QUY ĐỊNH CHUNG",
    "section": null,
    "section_title": null,
    "article": "Điều 1",
    "article_title": "Phạm vi điều chỉnh",
    "clause": "Khoản 1",
    "clause_header": null,
    "point": null
  },
  "source_file": "168.2024.NĐ.CP.docx"
}
```

**Case C — Điều không có Khoản** (`chunk_type: "ARTICLE_CHILD"`):

```json
{
  "chunk_id": "nd168_2024_dieu_55",
  "parent_id": "nd168_2024_dieu_55",
  "doc_id": "nd168_2024",
  "chunk_type": "ARTICLE_CHILD",
  "text_raw": "Bộ trưởng Bộ Công an, Bộ trưởng Bộ Tài chính...",
  "clause_header": null,
  "text_for_search": "Nghị định 168/2024/NĐ-CP. Điều 55. Trách nhiệm thi hành. Bộ trưởng Bộ Công an, Bộ trưởng Bộ Tài chính...",
  "legal_path": {
    "document_title": "Nghị định 168/2024/NĐ-CP",
    "chapter": "Chương IV",
    "chapter_title": "ĐIỀU KHOẢN THI HÀNH",
    "section": null,
    "section_title": null,
    "article": "Điều 55",
    "article_title": "Trách nhiệm thi hành",
    "clause": null,
    "clause_header": null,
    "point": null
  },
  "source_file": "168.2024.NĐ.CP.docx"
}
```

**Lưu ý quan trọng:** Với `ARTICLE_CHILD`, `chunk_id == parent_id` (cùng trỏ về Điều đó).

---

## 4. Text normalization — thực hiện TRƯỚC khi parse

Áp dụng cho tất cả paragraph text trước khi đưa vào state machine:

```python
def normalize_paragraph(text: str) -> str:
    text = text.replace('\xa0', ' ')   # non-breaking space — có trong Luật 36
    text = text.replace('​', '')  # zero-width space
    text = text.replace('’', "'") # curly apostrophe
    text = re.sub(r'\s+', ' ', text)   # collapse multiple spaces / tabs
    return text.strip()
```

Không được loại bỏ:
- Số tiền (200.000, 1.000.000, 70.000.000)
- Tên văn bản (168/2024/NĐ-CP)
- Ngày hiệu lực
- Mức phạt, điểm trừ GPLX

---

## 5. Parsing rules

### 5.1 Regex patterns — đã xác nhận trên 5 file thực tế

```python
import re

CHAPTER_PATTERN = re.compile(r'^(Chương|CHƯƠNG)\s+[IVXLCDM]+$', re.IGNORECASE)
SECTION_PATTERN  = re.compile(r'^(Mục|MỤC)\s+\d+$', re.IGNORECASE)
ARTICLE_PATTERN  = re.compile(r'^Điều\s+(\d+[a-zA-Z]?)\.\s*(.+)')
CLAUSE_PATTERN   = re.compile(r'^(\d{1,2})\.\s+(.+)')
POINT_PATTERN    = re.compile(r'^([a-zđ])\)\s*(.+)')
```

**Giải thích từng pattern:**

- `CHAPTER_PATTERN`: khớp đúng với `'Chương I'`, `'Chương II'`, `'CHƯƠNG IV'`. Dùng `$` để tránh match text dài hơn.
- `SECTION_PATTERN`: khớp với `'Mục 1'`, `'Mục 2'`. Luật 36 không có Mục — không vấn đề.
- `ARTICLE_PATTERN`: capture group 1 = số điều (`'7'`, `'35a'`), group 2 = title. Title luôn nằm cùng dòng — đã xác nhận.
- `CLAUSE_PATTERN`: chỉ match **1–2 chữ số** + dấu chấm + **space bắt buộc**. Clause cao nhất là 14 (NĐ168 Điều 6). Không match số tiền như `200.000` hay `1.000.000`.
- `POINT_PATTERN`: letters dùng trong thực tế: `a b c d đ e g h i k l m n o p q r s t`. Pattern `[a-zđ]` đủ dùng.

### 5.2 Preamble — bỏ qua trước Chương I / Điều 1

Tất cả 5 file đều có các paragraph preamble trước cấu trúc pháp luật:

```text
'NGHỊ ĐỊNH'
'Quy định xử phạt...'
'Căn cứ Luật Tổ chức Chính phủ...'
'Theo đề nghị của Bộ trưởng...'
'Chính phủ ban hành Nghị định...'
```

**Rule:** Parser bắt đầu gom dữ liệu **từ `Chương I` đầu tiên** (hoặc `Điều 1` nếu không có Chương). Tất cả paragraphs trước đó → bỏ qua hoàn toàn, không chunk.

Cài đặt: dùng flag `started = False`, set `True` khi gặp lần đầu CHAPTER_PATTERN hoặc ARTICLE_PATTERN.

### 5.3 Chapter/Section title — nằm ở PARAGRAPH TIẾP THEO

**Quan sát thực tế (tất cả 5 file đều nhất quán):**

```text
Paragraph N:   'Chương I'                          ← match CHAPTER_PATTERN
Paragraph N+1: 'NHỮNG QUY ĐỊNH CHUNG'              ← đây là chapter_title

Paragraph M:   'Mục 1'                             ← match SECTION_PATTERN
Paragraph M+1: 'VI PHẠM QUY TẮC GIAO THÔNG ĐƯỜNG BỘ' ← đây là section_title
```

**Rule:** Khi match Chapter hoặc Section, đọc thêm 1 paragraph tiếp theo làm title. Nếu paragraph tiếp theo match một pattern khác (tức là bắt đầu cấu trúc mới ngay) thì `chapter_title = None`.

### 5.4 Article title — nằm cùng dòng

```text
Paragraph: 'Điều 7. Xử phạt, trừ điểm giấy phép lái...'
            ^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
           số điều            article_title
```

ARTICLE_PATTERN group 2 capture thẳng title. Không cần đọc paragraph tiếp theo.

### 5.5 State machine — luồng đầy đủ

```text
started = False
current_chapter, current_chapter_title = None, None
current_section, current_section_title = None, None
current_article = None
current_clause  = None
current_level   = None  # 'article' | 'clause' | 'point'

Với mỗi paragraph p (đã normalize):

  Nếu chưa started:
    Nếu match CHAPTER hoặc ARTICLE → set started = True, xử lý tiếp
    Không thì: bỏ qua (preamble)

  Nếu đã started:
    [CHAPTER]
      → lưu current_chapter = p
      → đọc paragraph tiếp theo làm current_chapter_title (nếu không match pattern nào)
      → reset current_section, current_section_title, current_article, current_clause
      → current_level = None

    [SECTION]
      → lưu current_section = p
      → đọc paragraph tiếp theo làm current_section_title (nếu không match pattern nào)
      → reset current_article, current_clause
      → current_level = None

    [ARTICLE]
      → đóng article hiện tại (flush vào danh sách)
      → tạo article mới với title từ group 2 của regex
      → current_clause = None
      → current_level = 'article'

    [CLAUSE]
      → chỉ xử lý nếu current_article không None
      → đóng clause hiện tại (flush)
      → tạo clause mới, lưu clause_header = text của clause (phần sau số khoản)
      → current_level = 'clause'

    [POINT]
      → chỉ xử lý nếu current_clause không None
      → đóng point hiện tại (flush)
      → tạo point mới
      → current_level = 'point'

    [Không match pattern nào — continuation text]
      → nếu current_level == 'point':   nối vào point hiện tại
      → nếu current_level == 'clause':  nối vào clause hiện tại
      → nếu current_level == 'article': nối vào article hiện tại
      → nếu current_level == None:      bỏ qua
```

**Lưu ý continuation:** Có 54 paragraphs dạng continuation trong NĐ168 (khoảng 4% tổng paragraphs). Chúng là text bổ sung cho block hiện tại, nối bằng space: `current_block.text += ' ' + p`.

---

## 6. Chunking rules

### 6.1 Quyết định child type cho mỗi Điều

```text
Sau khi parse xong tất cả Khoản/Điểm của một Điều:

Case A — Khoản có Điểm:
  Parent = toàn bộ Điều
  Child  = từng Điểm (chunk_type = POINT)
  Điểm nào không có Khoản cha (orphan) → warning, bỏ qua

Case B — Khoản không có Điểm:
  Parent = toàn bộ Điều
  Child  = từng Khoản (chunk_type = CLAUSE)

Case C — Điều không có Khoản (body chỉ là plain text):
  Parent = Điều đó (chunk_type = ARTICLE)
  Child  = 1 chunk duy nhất (chunk_type = ARTICLE_CHILD)
  chunk_id == parent_id trong trường hợp này

Case D — Điều hỗn hợp (một số Khoản có Điểm, một số không):
  Child = từng Điểm của Khoản có Điểm (chunk_type = POINT)
        + từng Khoản không có Điểm (chunk_type = CLAUSE)
  → Đây là case bình thường trong luật VN
```

### 6.2 `text_for_search` — quy tắc tổng hợp

`text_for_search` là trường được đưa vào LightRAG. Nó phải chứa đủ context để LLM hiểu **mà không cần đọc parent**.

**Công thức chung:**

```text
text_for_search = [document_title]. [article]. [article_title]. [clause_header nếu có]. [point nếu có]. [text_raw].
```

**Ví dụ Case A (POINT):**

```text
Nghị định 168/2024/NĐ-CP.
Điều 7. Xử phạt, trừ điểm giấy phép lái của người điều khiển xe mô tô...
Khoản 1. Phạt tiền từ 200.000 đồng đến 400.000 đồng đối với người điều khiển xe thực hiện một trong các hành vi vi phạm sau đây:
Điểm a. Không chấp hành hiệu lệnh, chỉ dẫn của biển báo hiệu, vạch kẻ đường...
```

**Lý do bắt buộc include `clause_header`:** Nếu không có "Phạt tiền 200k-400k" trong chunk của Điểm a, LightRAG sẽ không biết hành vi này bị phạt bao nhiêu. Đây là **thông tin ngữ nghĩa quan trọng nhất** của NĐ168.

**Ví dụ Case B (CLAUSE, không có Điểm):**

```text
Nghị định 168/2024/NĐ-CP.
Điều 1. Phạm vi điều chỉnh.
Khoản 1. Nghị định này quy định về: xử phạt vi phạm hành chính...
```

**Ví dụ Case C (ARTICLE_CHILD):**

```text
Nghị định 168/2024/NĐ-CP.
Điều 55. Trách nhiệm thi hành.
Bộ trưởng Bộ Công an, Bộ trưởng Bộ Tài chính...
```

### 6.3 `text` của parent chunk

Parent `text` = ghép tất cả paragraphs thuộc Điều đó theo thứ tự, nối bằng `'\n'`. Giữ nguyên cấu trúc "1. ... a) ... b) ..." để đọc được.

---

## 7. ID convention

Tất cả ID phải stable, lowercase, dễ debug. Không dùng UUID.

```text
Article:  {doc_id}_dieu_{article_number}
Clause:   {doc_id}_dieu_{article_number}_khoan_{clause_number}
Point:    {doc_id}_dieu_{article_number}_khoan_{clause_number}_diem_{point_letter}
```

**Ví dụ:**

```text
nd168_2024_dieu_7
nd168_2024_dieu_7_khoan_1
nd168_2024_dieu_7_khoan_1_diem_a
nd168_2024_dieu_7_khoan_4_diem_d    ← chữ đ vẫn encode là 'd' trong ID
luat36_2024_dieu_12_khoan_3_diem_b
```

**Quy tắc encode đặc biệt cho ID:**

```text
- Chữ 'đ' trong point letter → encode thành 'dd' trong ID
  Ví dụ: Điểm đ → diem_dd (để tránh ký tự non-ASCII trong ID)
- Số điều giữ nguyên: Điều 7 → dieu_7, Điều 35 → dieu_35
- Số khoản giữ nguyên: Khoản 14 → khoan_14
```

**Với ARTICLE_CHILD:** `chunk_id = parent_id = {doc_id}_dieu_{n}`.

---

## 8. doc_id mapping

Lưu trong `src/lawgo_traffic/ingestion/doc_id_map.py`:

```python
DOC_ID_MAP = {
    "168.2024.NĐ.CP.docx": {
        "doc_id": "nd168_2024",
        "document_title": "Nghị định 168/2024/NĐ-CP",
    },
    "36:2024:QH15_luattrậttự.docx": {
        "doc_id": "luat36_2024",
        "document_title": "Luật Trật tự, An toàn Giao thông Đường bộ 36/2024/QH15",
    },
    "Luật-35-2024-QH15.docx": {
        "doc_id": "luat35_2024",
        "document_title": "Luật Đường bộ 35/2024/QH15",
    },
    "24_2023_TT-BCA_m_559088.docx": {
        "doc_id": "tt24_2023_bca",
        "document_title": "Thông tư 24/2023/TT-BCA",
    },
    "Nghị-định-336-2025-NĐ-CP.docx": {
        "doc_id": "nd336_2025",
        "document_title": "Nghị định 336/2025/NĐ-CP",
    },
}
```

Parser lấy `doc_id` và `document_title` từ dict này theo `os.path.basename(source_file)`. Không tự derive từ filename.

---

## 9. Làm sạch text

### 9.1 Được xóa / normalize

```text
- \xa0 (non-breaking space) → thay bằng space thường       [có trong Luật 36]
- ​ (zero-width space) → xóa
- ’ (curly apostrophe) → thay bằng '
- Multiple whitespace → collapse thành 1 space
- Strip đầu/cuối
```

### 9.2 Không được xóa

```text
- Số tiền: 200.000, 1.000.000, 70.000.000
- Số hiệu văn bản: 168/2024/NĐ-CP, 36/2024/QH15
- Điều/Khoản/Điểm identifiers
- Mức phạt, mức trừ điểm GPLX
- Ngày hiệu lực
- Tên Chương/Mục
```

---

## 10. Validation bắt buộc

Sau khi parse và chunk xong mỗi file, in report:

```json
{
  "source_file": "168.2024.NĐ.CP.docx",
  "doc_id": "nd168_2024",
  "total_articles": 55,
  "total_clauses": 332,
  "total_points": 910,
  "parents_count": 55,
  "children_count": 950,
  "children_by_type": {
    "POINT": 910,
    "CLAUSE": 38,
    "ARTICLE_CHILD": 2
  },
  "warnings": []
}
```

**Warning triggers:**

```text
W01 — Khoản không thuộc Điều nào (orphan clause)
W02 — Điểm không thuộc Khoản nào (orphan point)
W03 — Điều không tạo được parent_id (thiếu số điều)
W04 — child chunk text_raw quá ngắn (< 10 ký tự)
W05 — duplicate chunk_id
W06 — child chunk thiếu clause_header khi chunk_type = POINT
W07 — ARTICLE_CHILD nhưng Điều có > 0 Khoản (logic conflict)
```

---

## 11. Expected counts — để verify sau khi implement

Dựa trên phân tích thực tế:

| doc_id | articles | clauses | points | est. children |
|--------|----------|---------|--------|----------------|
| nd168_2024 | 55 | 332 | 910 | ~950 |
| luat36_2024 | 89 | 440 | 443 | ~530 |
| luat35_2024 | 86 | 388 | 383 | ~470 |
| tt24_2023_bca | 40 | 165 | 175 | ~215 |
| nd336_2025 | 28 | 120 | 294 | ~320 |
| **Tổng** | **298** | **1445** | **2205** | **~2485** |

Children ước tính cao hơn points vì CLAUSE và ARTICLE_CHILD cũng tạo child chunks.

---

## 12. Acceptance criteria

Module đạt yêu cầu khi:

```text
1. Parse được cả 5 file trong data/raw/ — không crash.
2. Sinh được parents.jsonl và children.jsonl hợp lệ JSON.
3. Mỗi child chunk đều có parent_id trỏ về Điều tương ứng.
4. Mỗi child chunk đều có legal_path đầy đủ (không null trừ các field hợp lệ).
5. text_for_search của POINT chunk chứa clause_header (có mức phạt nếu là NĐ).
6. Không có duplicate chunk_id (kiểm tra toàn bộ 5 file cộng lại).
7. Validation report không có W01, W02, W05 (orphan và duplicate là lỗi nghiêm trọng).
8. Article count khớp expected counts trong bảng Section 11 (±5%).
9. Kiểm tra thủ công 10 chunk của NĐ168: mỗi chunk phải thấy rõ mức phạt.
10. Chunk ARTICLE_CHILD không xuất hiện cho Điều có Khoản.
```

---

## 13. Không làm trong spec này

```text
- Không gọi LLM
- Không build LightRAG, Qdrant, Neo4j
- Không trả lời user
- Không OCR/PDF scan
- Không xử lý bảng (table) trong Word — các file hiện tại không có bảng chứa luật
```

Module này chỉ chịu trách nhiệm: **Word sạch → structured legal chunks với đầy đủ context**.
