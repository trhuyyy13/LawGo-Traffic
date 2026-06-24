# 04_SPEC — Multi-format Ingestion (PDF text-layer + OCR)

> Dự án: LawGo Traffic — AI Legal Advisory Agent
> Module: Ingestion (mở rộng spec 01)
> Mục tiêu: Cho phép `data/raw/` chứa `.docx`, `.doc`, và `.pdf` (cả pdf có text layer và pdf scan ảnh), mà không phải sửa `legal_parser.py` hay `chunk_builder.py`.
> Phiên bản: 1.0
> Quan hệ với spec khác: kế thừa contract `{source_file, doc_id, document_title, paragraphs}` đã định nghĩa ở `01_spec_legal_parser_and_chunking.md`. Không thay thế spec 01, chỉ thêm các nguồn extract mới đổ vào cùng contract đó.

---

## 1. Bối cảnh và mục tiêu

Tính đến thời điểm viết spec này, `data/raw/` có 5 file `.docx` (đã chunk xong ở spec 01) và 11 file mới tải từ `vbpl.vn`/`vanban.chinhphu.vn`:

```text
9 file "chính văn" cần đưa vào pipeline:
  - 1 file .doc       (Luật Xử lý VPHC gốc)
  - 7 file .pdf có text layer
  - 1 file .pdf scan ảnh (không có text layer)

2 file "phụ lục" (Phụ lục kèm Thông tư) — XEM MỤC 9, ngoài phạm vi spec này.
```

`legal_parser.py` hiện chỉ nhận input từ `docx_extractor.extract_docx_to_text()`. Spec này thêm các extractor mới cho `.doc`/`.pdf`, tất cả đổ ra đúng schema cũ để pipeline phía sau (`legal_parser.py`, `chunk_builder.py`, `validation_report`) không cần sửa.

**Phát hiện kỹ thuật làm nền cho thiết kế** (đã verify trực tiếp trên file thật, không phải giả định):
- `pdftotext` (poppler) trích xuất sạch tiếng Việt có dấu trên cả 7 file pdf text-layer — không cần xử lý mojibake.
- `pdftotext` (không dùng `-layout`) trả về line theo ngắt dòng hiển thị (visual line-wrap), KHÔNG theo đoạn văn logic như docx. Nhưng `legal_parser.py` (dòng 225-235, `_LegalDocParser.process`) đã có sẵn nhánh "continuation text": bất kỳ dòng nào không khớp `CHAPTER/SECTION/ARTICLE/CLAUSE/POINT_PATTERN` sẽ được nối (`+= " " + p`) vào block hiện tại. Vì mỗi marker cấu trúc (`Điều N.`, `1.`, `a)`) luôn nằm đầu dòng riêng trong layout gốc, cơ chế này xử lý đúng việc PDF bị ngắt dòng giữa câu mà không cần sửa parser.
- File `Thong-tu-72-2024-TT-BCA-dieutra-tainangiaothong.pdf` là ảnh scan thật (`pdfinfo` → `Creator: Scanner System`; `pdftotext` toàn văn 33 trang chỉ ra 33 byte ký tự). Đây là trường hợp duy nhất hiện tại cần OCR.

---

## 2. Input — danh sách 9 file đưa vào pipeline lần này

| filename (`data/raw/`) | doc_id | document_title | extraction_method |
|---|---|---|---|
| `Luat-15-2012-QH13-XLVPHC.doc` | `luat_xlvphc_2012` | Luật Xử lý vi phạm hành chính 15/2012/QH13 | `doc_to_docx` |
| `Luat-67-2020-QH14-XLVPHC-suadoi.pdf` | `luat_xlvphc_2020` | Luật sửa đổi, bổ sung Luật XLVPHC 67/2020/QH14 | `pdf_text` |
| `Luat-88-2025-QH15-XLVPHC-suadoi.pdf` | `luat_xlvphc_2025` | Luật sửa đổi, bổ sung Luật XLVPHC 88/2025/QH15 | `pdf_text` |
| `Thong-tu-35-2024-TT-BGTVT-daotao-GPLX.pdf` | `tt35_2024_bgtvt` | Thông tư 35/2024/TT-BGTVT (đào tạo lái xe) | `pdf_text` |
| `Thong-tu-12-2025-TT-BCA-sathach-capGPLX.pdf` | `tt12_2025_bca` | Thông tư 12/2025/TT-BCA (sát hạch, cấp GPLX) | `pdf_text` |
| `Thong-tu-47-2024-TT-BGTVT-kiemdinh-xecogioi.pdf` | `tt47_2024_bgtvt` | Thông tư 47/2024/TT-BGTVT (đăng kiểm xe cơ giới) | `pdf_text` |
| `Nghi-dinh-67-2023-ND-CP-baohiem-bat-buoc-xecogioi.pdf` | `nd67_2023` | Nghị định 67/2023/NĐ-CP (bảo hiểm bắt buộc xe cơ giới) | `pdf_text` |
| `Thong-tu-72-2024-TT-BCA-dieutra-tainangiaothong.pdf` | `tt72_2024_bca` | Thông tư 72/2024/TT-BCA (điều tra, giải quyết TNGT) | `pdf_ocr` |
| `Thong-tu-51-2024-TT-BGTVT-QCVN41-2024-baohieuduongbo.pdf` | `tt51_2024_bgtvt` | Thông tư 51/2024/TT-BGTVT (ban hành QCVN 41:2024/BGTVT) | `pdf_text` |

Mapping này được thêm vào `DOC_ID_MAP` trong `src/lawgo_traffic/ingestion/doc_id_map.py` — cùng dict, cùng quy ước với 5 entry cũ.

**Lưu ý quan trọng về độ phủ:** file `Thong-tu-51-2024...` ở trên chỉ là văn bản ban hành (1 trang, nội dung chủ yếu là hiệu lực/căn cứ pháp lý). Toàn bộ nội dung kỹ thuật của QCVN 41:2024 (định nghĩa từng loại biển báo, vạch kẻ đường) nằm trong file Phụ lục 403 trang — file này KHÔNG được chunk ở spec này (xem Mục 9). Nghĩa là sau spec này, intent "biển báo & vạch kẻ" vẫn **chưa** có dữ liệu tra cứu chi tiết theo từng biển — chỉ có phần khung pháp lý. Cần một spec riêng cho dữ liệu dạng bảng/hình ảnh.

---

## 3. Kiến trúc tổng thể

```text
data/raw/*.{docx,doc,pdf}
        │
        ▼
ingestion/extract_router.py   ← MỚI — entrypoint thay cho extract_all_docx
        │
   ┌────┼──────────────┬───────────────────┐
   ▼    ▼              ▼                   ▼
.docx   .doc           .pdf (text layer)   .pdf (scan ảnh)
  │      │                    │                   │
  │      ▼                    ▼                   ▼
  │  soffice --headless   pdf_text_extractor   pdf_ocr_extractor
  │  --convert-to docx    .py (MỚI)            .py (MỚI, OCR_ENABLED)
  │      │                    │                   │
  │      ▼                    │                   │
  └─► docx_extractor.py ◄─────┴───────────────────┘
      (KHÔNG ĐỔI)                  │
                                   ▼
                {source_file, doc_id, document_title,
                 paragraphs: list[str], extraction_method: str}
                   (contract cũ + 1 field mới, optional,
                    default "docx" để tương thích 5 file cũ)
```

Nguyên tắc thiết kế: **mọi extractor mới chỉ cần sản xuất đúng `paragraphs: list[str]`**. `legal_parser.py`, `chunk_builder.py`, `id_utils.py` không đổi một dòng nào.

---

## 4. Module mới: `ingestion/extract_router.py`

```python
def detect_format(filepath: str) -> str:
    """Trả về 'docx' | 'doc' | 'pdf_text' | 'pdf_ocr' dựa trên đuôi file + heuristic."""

def extract_all(raw_dir: str, output_dir: str) -> list[str]:
    """Quét raw_dir, route từng file theo detect_format(), gọi extractor tương ứng,
    lưu JSON vào output_dir. Trả về list path đã lưu. Logic giống extract_all_docx
    hiện tại (skip + print warning nếu file không có trong DOC_ID_MAP)."""
```

`scripts/ingest_docx.py` đổi import từ `extract_all_docx` sang `extract_all` (đường dẫn/CLI args không đổi). Script này nên được rename thành `scripts/ingest_raw.py` để phản ánh đúng việc nó không còn chỉ xử lý docx — nhưng việc rename không bắt buộc trong spec này, có thể giữ tên cũ để giảm thay đổi.

### 4.1 Logic `detect_format`

```text
1. Đuôi .docx                              → "docx"
2. Đuôi .doc                               → "doc"
3. Đuôi .pdf:
   a. Chạy `pdftotext <file> -` lấy toàn văn
   b. tính avg_chars_per_page = len(text.strip()) / số_trang (pdfinfo -> Pages)
   c. nếu avg_chars_per_page < 20           → "pdf_ocr"
      ngược lại                             → "pdf_text"
4. Đuôi khác                                → raise ValueError (không hỗ trợ)
```

Ngưỡng 20 ký tự/trang được chọn dựa trên số liệu thực tế đã đo: file scan (Thong-tu-72) ≈ 1 ký tự/trang; mọi file text-layer khác ≥ hàng nghìn ký tự/trang. Biên độ an toàn rất lớn, không cần tinh chỉnh thêm trong v1.

---

## 5. Module mới: `ingestion/pdf_text_extractor.py`

```python
def extract_pdf_to_text(input_path: str) -> dict:
    """Giống extract_docx_to_text nhưng dùng pdftotext.

    1. subprocess: `pdftotext <input_path> -` (không dùng -layout — xem lý do Mục 1)
    2. Tách theo "\n" thành list[str]
    3. normalize_paragraph() từng dòng (dùng lại từ utils/text_normalizer.py)
    4. Lọc nhiễu cấp trang: dòng chỉ chứa số trang đơn lẻ (regex r"^\d{1,4}$")
       hoặc dòng lặp lại y hệt ở đầu mỗi trang (header/footer) → bỏ qua
       (không append vào continuation, để không làm bẩn body_text)
    5. Trả về {source_file, doc_id, document_title, paragraphs, extraction_method: "pdf_text"}
    """
```

`extract_all_pdf_text(raw_dir, output_dir)` — hàm batch tương tự `extract_all_docx`, dùng nội bộ bởi router (không phải gọi trực tiếp từ script).

**Lý do không dùng `pdftotext -layout`:** đã test trực tiếp — `-layout` thêm khoảng trắng canh cột (leading spaces) vào đầu dòng, không cải thiện độ chính xác parser (parser dùng `^` anchor + `.strip()` nên không quan trọng) nhưng làm `normalize_paragraph` phải xử lý nhiều whitespace thừa hơn. Bản không `-layout` cho output sạch hơn.

---

## 6. Module mới: `ingestion/pdf_ocr_extractor.py`

Chỉ kích hoạt khi `settings.ocr_enabled = True` (xem Mục 7). Nếu `OCR_ENABLED=false` và router gặp file `pdf_ocr`, **router raise lỗi rõ ràng** (không silent-skip) yêu cầu set flag — tránh tạo ra file extracted rỗng/sai mà không ai biết.

```python
def extract_scanned_pdf_to_text(input_path: str) -> dict:
    """
    1. `pdfimages -all <input_path> <tmp_prefix>` — lấy đúng ảnh JPEG gốc nhúng
       trong từng trang (KHÔNG render lại qua pdftoppm — ảnh gốc giữ nguyên
       chất lượng scan, tránh mất chi tiết do resample).
    2. Với mỗi ảnh trang (theo thứ tự trang), gọi OpenAI vision (model =
       settings.ocr_model, mặc định "gpt-5.4-mini") với PROMPT_OCR (Mục 6.1).
    3. Ghép text các trang theo thứ tự, mỗi trang cách nhau "\n".
    4. Tách "\n" → paragraphs, normalize giống pdf_text_extractor.
    5. Trả về dict cùng schema, extraction_method: "pdf_ocr".
    6. Lưu riêng RAW response của từng trang vào
       data/extracted/_ocr_debug/<doc_id>_page_<n>.txt để tiện soát lỗi
       (không phải file chunking, chỉ để review thủ công).
    """
```

### 6.1 Prompt OCR (verbatim transcription, không diễn giải)

```text
Đây là ảnh scan một trang văn bản pháp luật Việt Nam. Hãy phiên âm (transcribe)
CHÍNH XÁC TỪNG CHỮ những gì nhìn thấy trong ảnh, theo các quy tắc sau:

1. KHÔNG diễn giải, KHÔNG tóm tắt, KHÔNG sửa lỗi chính tả, KHÔNG thêm nội dung
   không có trong ảnh.
2. Giữ nguyên chính xác số hiệu Điều, Khoản, Điểm (ví dụ "Điều 5.", "2.", "a)")
   — đây là phần quan trọng nhất, sai một số là sai trích dẫn pháp lý.
3. Giữ nguyên ngắt đoạn: mỗi Điều/Khoản/Điểm xuống dòng riêng như trong ảnh.
4. Nếu có chữ không đọc được rõ, đánh dấu bằng [KHÔNG RÕ: <phần đoán tốt nhất>]
   thay vì bỏ qua hoặc đoán bừa không đánh dấu.
5. Bỏ qua header/footer/số trang/dấu mộc/chữ ký scan — chỉ lấy nội dung văn bản.
6. Output thuần text, không markdown, không thêm chú thích ngoài nội dung gốc.
```

Yêu cầu (4) là cơ chế chính để tuân thủ nguyên tắc "No citation → no confident answer" — bất kỳ đoạn nào model không chắc sẽ tự đánh dấu, không bị chunk_builder/legal_parser âm thầm coi là văn bản chính thức.

### 6.2 Chi phí ước tính

Với `gpt-5.4-mini` ($0.75 / 1M input tokens, $4.50 / 1M output tokens): 33 trang × (~1500 input token ảnh + ~800 output token text)/trang ≈ **dưới $0.20 cho cả Thông tư 72**. Không đáng kể, không cần ngân sách riêng — chạy lại nếu cần (re-OCR) cũng không phải vấn đề chi phí.

---

## 7. Config / gating

Thêm vào `src/lawgo_traffic/config.py` (theo đúng pattern `voice_enabled` đã có):

```python
# OCR (set OCR_ENABLED=true to activate; reuses LLM_API_KEY)
ocr_enabled: bool = False
ocr_model: str = "gpt-5.4-mini"
```

Thêm vào `.env.example` (và `.env` thật của user — xem Mục 10):

```env
# ── OCR (set OCR_ENABLED=true to activate; reuses LLM_API_KEY above) ────
OCR_ENABLED=false
OCR_MODEL=gpt-5.4-mini
```

OCR dùng lại `LLM_API_KEY`/`LLM_PROVIDER` đã có sẵn trong Settings — không thêm key riêng, vì cùng là OpenAI key của user.

---

## 8. Error handling

```text
- pdftotext / pdfinfo / pdfimages không có trong PATH
    → raise RuntimeError rõ ràng ("poppler-utils chưa được cài, brew install poppler"),
      không fallback âm thầm.
- File .pdf bị mã hoá / pdftotext trả exit code != 0
    → raise, log tên file, KHÔNG bỏ qua file (khác với .docx không nằm trong
      DOC_ID_MAP — trường hợp đó mới được skip).
- Gọi OpenAI vision lỗi (timeout/rate limit)
    → retry tối đa 2 lần với backoff, sau đó raise — KHÔNG trả về paragraphs
      rỗng/một phần (tránh chunk thiếu mà không ai biết).
- Trang OCR có nhiều marker "[KHÔNG RÕ: ...]"
    → chunk_builder validation (Mục 9 spec 01 — validation_report.json) thêm
      warning code mới: "W05: low-confidence OCR text in <chunk_id>" khi
      đếm thấy "[KHÔNG RÕ:" trong text_raw của chunk. Đây chỉ là warning,
      không block pipeline — nhưng phải xuất hiện rõ trong validation_report
      để biết chunk nào cần người review tay trước khi tin dùng.
```

---

## 9. Ngoài phạm vi spec này (explicit out-of-scope)

```text
- Phụ lục dạng bảng/hình ảnh (Thong-tu-35-...-PhuLuc.pdf,
  Thong-tu-51-...-PhuLuc.pdf — chứa mẫu biểu, hình vẽ biển báo) — không có
  cấu trúc Điều/Khoản/Điểm, legal_parser hiện tại không áp dụng được.
  Cần spec riêng cho dữ liệu dạng bảng/hình (có thể là: trích từng biển báo
  thành 1 "card" có ảnh + mô tả, lưu riêng, không qua legal_parser).
- Gộp 3 văn bản Luật XLVPHC (gốc 2012 + sửa đổi 2020 + sửa đổi 2025) thành
  1 "bản hợp nhất" logic — đây là việc của graph layer (edge AMENDS đã có
  sẵn trong graph/schema.py), không phải việc của ingestion.
- Tổng quát hoá xử lý .doc cho nhiều file .doc trong tương lai (ở đây chỉ
  có 1 file .doc, xử lý bằng 1 lệnh `soffice --headless --convert-to docx`
  gọi từ router — nếu sau này có nhiều file .doc, có thể cần làm thêm
  retry/error-handling kỹ hơn cho bước convert, không nằm trong v1 này).
- OCR cho ảnh không phải PDF (jpg/png rời) — không có file nào dạng này hiện tại.
- Local OCR (Tesseract) — đã cân nhắc ở phần brainstorming, không chọn vì
  user ưu tiên dùng OpenAI key sẵn có.
```

---

## 10. Việc cần làm ngoài code (do user thực hiện)

```text
- Cài poppler-utils nếu chưa có: `brew install poppler` (pdftotext/pdfinfo/
  pdfimages đã có sẵn trên máy hiện tại theo kiểm tra `which pdftotext`).
- Cài LibreOffice (cho bước .doc → .docx): `brew install --cask libreoffice`.
- Điền OPENAI key thật vào `.env` (file `.env.example` đã có field
  LLM_API_KEY, OCR_ENABLED, OCR_MODEL — copy sang `.env` rồi điền key).
```

---

## 11. Test cases tối thiểu

```text
1. extract_pdf_to_text() trên Thong-tu-47 (pdf text layer) → so số "Điều N."
   tìm được trong paragraphs với số Điều đếm tay/grep trên pdftotext output,
   phải khớp.
2. detect_format() trên Thong-tu-72 (scan) → phải trả "pdf_ocr", không phải
   "pdf_text" (test bằng số liệu char-density đã biết).
3. detect_format() khi OCR_ENABLED=false và gặp file "pdf_ocr" → router
   raise lỗi rõ ràng, không tạo file extracted rỗng.
4. paragraphs từ pdf_text_extractor feed thẳng vào parse_legal_document()
   (không sửa gì) → ra ArticleBlock list không rỗng, không có warning
   "W01/W02 orphan clause/point" bất thường (vài warning W04 short text
   là chấp nhận được, giống 5 file cũ).
5. (Nếu OCR_ENABLED=true, cần OpenAI key thật — test này là integration
   test, không chạy trong CI mặc định) extract_scanned_pdf_to_text() trên
   Thong-tu-72 → paragraphs không rỗng, validation_report có thể có W05.
```

---

## 12. Acceptance criteria

```text
- Chạy `python scripts/ingest_docx.py` (hoặc script đã đổi tên) trên
  data/raw/ hiện tại (14 file: 5 cũ + 9 mới, KHÔNG tính 2 phụ lục) ra đủ
  9 file JSON mới trong data/extracted/, không file nào rỗng paragraphs.
- legal_parser.py và chunk_builder.py không bị sửa (diff = 0 trên 2 file này).
- validation_report.json sau khi build_chunks chạy lại có entry cho cả
  9 doc_id mới, không có warning mức nghiêm trọng (orphan clause/point)
  ngoại trừ W04 (short text) đã quen thuộc từ trước.
- Với OCR_ENABLED=false, file Thong-tu-72 KHÔNG bị silent-skip — pipeline
  báo lỗi rõ ràng yêu cầu set OCR_ENABLED=true.
```
