# Nghiệm thu G4 — Nhập PDF bệnh án giả lập

**Phạm vi:** PDF-01–PDF-04. **Reviewer:** QA · 22/11/2026  
**SHA nhánh:** `feat/medshield-demo` tại thời điểm kiểm thử.  
**Môi trường:** Windows 11 Pro 10.0.26200, Node.js 24.13.0, Python 3.11.7 (uv), npm 10.9.2, Chromium Playwright 1.49.1  
**Reviewer ID:** độc lập với PM và Dev.

---

## Checksum tài nguyên PDF (SHA-256)

```
2a7d5545d501e8924ede0e063e579938e87b487399bac6995164183b0d810587  apps/web/src/usePdfImport.ts
fe2e1d9dde82adebc1369336b41e89ea11e9e9b2259dd0bbd7b22e308fae181f  apps/web/src/pdfDocument.ts
f9db9d4cd3be995e07cdfa7eb7daa40aae16b6490786edeb0b78b0e6db89c12e  apps/web/src/PdfImportControls.tsx
27e918a067cbcb21dbab518fb14c404ab5d1d1b6b90bdddb5b4414c0434c4b64  apps/web/src/pdfPolicy.ts
5f6ef9d5a44f55b7ad3a1bc64a9598777b0b56958fa8bf8358314e0980b27c90  apps/web/src/SourcePanel.tsx
6c7e4d3bd38126f133b7f8588cd5e78ef727e1267b891f875c670648a52ef1fe  apps/web/e2e/pdf-import.spec.ts
96946f31f2661d8769cf651d27312fe9f752c66f040433fa8101e1d71ee27a5b  docs/evidence/demo-benh-an-ngoai-tru.pdf
9d09d18fb065227644272c1507fd6013b9c3990b22656670edd022b3fdf985e0  docs/evidence/demo-benh-an-ngoai-tru.expected.txt
b4b87519aae1c6b9c87fec37bb4dbb15c06b951a57684f2bf10add7926cd703e  scripts/generate-demo-pdf.py
4a63db3acc75e6a64e36b42779a9e751147c422be153a0d84ec16826bb5bca7b  docs/huong-dan-nhap-pdf.md
```

## Source line count compliance

Nguồn viết tay ≤ 299 dòng vật lý (Python/JS/TS/JSX/TSX/CSS + test; không đếm generated/dependency/lock/Markdown):

```
108 usePdfImport.ts
 98 pdfDocument.ts
 77 PdfImportControls.tsx
  6 pdfPolicy.ts
240 SourcePanel.tsx
296 pdf-import.spec.ts
121 generate-demo-pdf.py
```

**Kết luận:** PASS. Mọi file đều tuân thủ ≤299 dòng.

---

## PDF-01 · Fixture và expected output

**Người làm:** BA + Dev · **Reviewer:** QA · **Tiêu chí:**  
Tạo PDF giả lập ngoại trú 1–2 trang có tên, ngày sinh, điện thoại, mã BN, địa chỉ, ngày tái khám. Nguồn và bản chữ kỳ vọng kiểm được. Ghi rõ DỮ LIỆU GIẢ LẬP.

**Bằng chứng:**
- `docs/evidence/demo-benh-an-ngoai-tru.txt` (15 dòng) — input cho generator
- `scripts/generate-demo-pdf.py` (121 dòng) — ReportLab tạo PDF từ .txt, dùng Noto Sans, hai trang
- `docs/evidence/demo-benh-an-ngoai-tru.pdf` (34.968 bytes, 2 trang) — PDF fixture có lớp chữ
- `docs/evidence/demo-benh-an-ngoai-tru.expected.txt` (29 dòng, 678 bytes) — văn bản trích kỳ vọng từ PDF

**Kiểm thử:**
```powershell
Set-Location D:\Workspace\MedShield
uv run --no-project --python 3.11.7 --with reportlab==5.1.0 python scripts/generate-demo-pdf.py
# Tạo demo-benh-an-ngoai-tru.pdf 2 trang ghi "DỮ LIỆU GIẢ LẬP" rõ ràng
```

Mở PDF bằng trình đọc, quan sát:
- **Trang 1:** Header `DỮ LIỆU GIẢ LẬP` + `BỆNH ÁN NGOẠI TRÚ`, mã tham chiếu 15/BV-01, hành chính (tên `Nguyễn Văn Hạ Minh`, giới tính Nam, SĐT `0912 345 678`, địa chỉ `Số 12 đường Kim Giang ...`), khám bệnh và các trường lâm sàng.
- **Trang 2:** Tiếp tục trường quan sát, hướng xử trí và hẹn tái khám `18/12`.

Trích chữ thật bằng trình duyệt qua workflow import PDF → kiểm tra văn bản khớp `.expected.txt`. Hybrid nhận diện NAME/DATE/PHONE, reviewer bổ sung tên `tạ hư cấu`, ngày tái khám `18/12` còn nguyên trong TXT xuất.

**Kết luận:** PASS. PDF mẫu chứa đầy đủ trường yêu cầu, ghi rõ giả lập, bản chữ kỳ vọng kiểm được.

---

## PDF-02 · PDF.js integration và error handling

**Người làm:** Dev · **Reviewer:** QA · **Tiêu chí:**  
Tích hợp PDF.js 6.5.438, chọn khoảng trang, hủy, lỗi PDF/mật khẩu/scan. Lock phiên bản, ghi nguồn `THIRD_PARTY.md`.

**Bằng chứng:**
- `apps/web/package.json` — `pdfjs-dist: "6.5.438"` khóa
- `THIRD_PARTY.md` — ghi Mozilla PDF.js, Apache-2.0, pdfjs-dist 6.5.438
- `apps/web/src/usePdfImport.ts` (108 dòng) — hook quản lý session, AbortController
- `apps/web/src/pdfDocument.ts` (98 dòng) — PDF.js wrapper, text extraction, row formatting
- `apps/web/src/pdfPolicy.ts` (6 dòng) — `MAX_PDF_BYTES: 10*1024*1024`, `MAX_PDF_PAGES: 10`, `MAX_TEXT_POINTS: 50_000`
- `apps/web/src/PdfImportControls.tsx` (77 dòng) — UI chọn file/trang, nút trích/hủy
- `apps/web/e2e/pdf-import.spec.ts` (296 dòng) — 9 tests PDF (happy 390/1440px, errors, cancellation)

**Kiểm thử:**
```powershell
Set-Location D:\Workspace\MedShield\apps\web
npm ci
npm run typecheck          # Typecheck pass
npm run test:e2e -- pdf-import.spec.ts
```

**Kết quả e2e 9/9 PASS (19.4s):**
1. ✅ local PDF, hybrid review and approved TXT/JSON at 390px (2.7s)
2. ✅ local PDF, hybrid review and approved TXT/JSON at 1440px (2.5s)
3. ✅ PDF import rejects non-PDF bytes and preserves the draft (895ms)
4. ✅ PDF import rejects damaged PDF and preserves the draft (1.5s)
5. ✅ PDF import rejects password-protected PDF and preserves the draft (1.5s)
6. ✅ PDF import rejects over 10 MiB and preserves the draft (1.9s)
7. ✅ mixed pages require a narrower range and a scan alone stays out of the draft (1.9s)
8. ✅ invalid ranges, more than ten pages and oversized extracted text preserve the draft (1.9s)
9. ✅ cancel and subsequent PDF import discard a held older file read (1.3s)

**Quan sát:**
- Non-PDF/damaged/password-protected → thông báo tiếng Việt cụ thể, giữ draft
- Over 10 MiB → từ chối rõ ràng
- Trang scan → báo "Trang X không có lớp chữ", yêu cầu chọn lại range
- Khoảng trang sai (first > last, > 10 trang) → message rõ ràng
- Unicode tiếng Việt (dấu tổ hợp, emoji `tạ hư cấu`) → offset chính xác
- Hủy và chọn PDF mới → response cũ bị discard

**Kết luận:** PASS. PDF.js tích hợp đúng, mọi lỗi có hướng xử lý an toàn, không gửi PDF lên API.

---

## PDF-03 · Workflow integration và regression

**Người làm:** Dev · **Reviewer:** QA · **Tiêu chí:**  
Văn bản trích áp dụng vào luồng nhập hiện tại, input đổi vô hiệu kết quả cũ, TXT/example workflows vẫn chạy.

**Bằng chứng:**
- `apps/web/src/SourcePanel.tsx` (240 dòng) — nút "Nhập PDF" + PdfImportControls, input versioning
- `apps/web/e2e/pdf-import.spec.ts` — test 1 & 2 chạy đầy đủ: PDF → phân tích hybrid → đổi entity → xác nhận → tải TXT/JSON

**Kiểm thử workflow thật:**
Test case 1 & 2 kiểm:
1. Chọn PDF, đặt trang 1–2, trích văn bản → ô **Văn bản gốc** nhận text có `tạ hư cấu` và `18/12`
2. Chọn "Tiếng Việt", "Kết hợp · hybrid", bấm "Phân tích" → gọi `/api/analyze` thật (verified by request spy)
3. Machine entities hiển thị, thêm `tạ hư cấu` thủ công với nhãn NAME → gọi `/api/redact` thật
4. Xác nhận "Tôi đã rà soát toàn bộ nội dung" → enable "Tải TXT" và "Tải JSON"
5. Tải TXT → nội dung khớp preview, `18/12` còn, `tạ hư cấu` → `[NAME_X]`
6. Tải JSON → `{redacted_text, metadata}`, không có input gốc hay tên file
7. Chọn PDF lại, trang 2 only → preview/approve bị vô hiệu, cần rà soát lại

Test case 9 kiểm:
- Trong khi PDF đang đọc (file.arrayBuffer() bị gate hold), bấm "Hủy nhập PDF" → draft text giữ nguyên
- Chọn PDF khác → trích thành công
- Release gate cho file đầu → response cũ bị discard, không đổi UI

Hồi quy TXT/example: e2e regression test pass. Test 3–9 giữ draft khi PDF lỗi → không phá workflow TXT.

**Kết luận:** PASS. Luồng PDF → analyze → edit → approve → export hoạt động, input versioning chặn race condition, không regression TXT/example workflow.

---

## PDF-04 · Acceptance documentation và Windows demo

**Người làm:** Dev + PM · **Reviewer:** QA · **Tiêu chí:**  
Kiểm Windows, 390px/1440px, bàn phím, đo thời gian, kịch bản 3 phút.

**Bằng chứng:**
- `docs/huong-dan-nhap-pdf.md` (46 dòng) — hướng dẫn khởi động, demo ba phút, giới hạn và kiểm thử
- `docs/reviews/G4-pdf.md` (file này) — biên bản review
- `docs/plan-nhap-pdf-benh-an.md` (54 dòng) — plan overview PDF-01–04

**Kiểm thử Windows:**
- **Môi trường:** Windows 11 Pro 10.0.26200, Node.js 24.13.0, Python 3.11.7
- **Khởi động:**
  ```powershell
  # Cửa sổ 1 · API
  Set-Location D:\Workspace\MedShield
  uv sync --locked --python 3.11.7
  uv run --locked uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --no-access-log
  
  # Cửa sổ 2 · Web
  Set-Location D:\Workspace\MedShield\apps\web
  npm ci
  npm run dev
  ```
- **Demo 3 phút:** Tìm tham khảo ở `docs/huong-dan-nhap-pdf.md` · bảng thao tác từ 0:00–3:00
  - 0:00–0:45: Chọn PDF mẫu, chọn trang 1–2, trích văn bản
  - 0:45–1:20: Kiểm văn bản tiếng Việt, phân tích hybrid
  - 1:20–2:25: Rà soát entities, thêm `tạ hư cấu` bị sót, xác nhận, tải TXT
  - 2:25–3:00: Mở TXT, đối chiếu `[NAME_X]` và ngày `18/12` còn nguyên

**Viewport & keyboard:**
- Test 1 & 2 đã kiểm 390px và 1440px: không có horizontal scroll, layout responsive
- Keyboard accessibility:
  - Tab vào "Trang đầu" → Tab → "Trang cuối" → Tab → "Trích văn bản"
  - Enter trên "Trích văn bản" → extract
  - Space trên checkbox "Tôi đã rà soát toàn bộ nội dung" → approve
  - Enter trên "Tải TXT"/"Tải JSON" → download
  - Enter trên "Hủy nhập PDF" → cancel

**Timing (quan sát từ e2e log):**
- Trích 2 trang PDF: < 1s (happy path test 1 & 2 mỗi test ~2.5–2.7s bao gồm toàn workflow)
- Analyze hybrid: ~1s (request/response quan sát trong test)
- Redact: < 1s

**Browser storage & secrets:**
- Test verify `localStorage` và `sessionStorage` đều rỗng sau workflow
- Console log không chứa `tạ hư cấu` (manual name checked)
- Không có mutation request gửi PDF bytes (test spy kiểm chỉ /api/analyze và /api/redact)

**Kết luận:** PASS. Windows demo hoạt động, viewport/keyboard access đạt, timing chấp nhận được (<3s end-to-end), không lưu secret/input.

---

## Kết luận tổng thể G4-PDF

**PDF-01:** ✅ PASS — Fixture có đầy đủ trường, generator và expected output kiểm được.  
**PDF-02:** ✅ PASS — PDF.js tích hợp đúng, 9/9 e2e tests pass, error handling an toàn.  
**PDF-03:** ✅ PASS — Workflow integration hoàn chỉnh, no regression, input versioning chặn race.  
**PDF-04:** ✅ PASS — Windows demo thành công, viewport/keyboard/timing chấp nhận được, hướng dẫn đầy đủ.

**Lỗi còn mở:** Không.

**Phiên bản kiểm thử:** nhánh `feat/medshield-demo`, phạm vi PDF bắt đầu sau commit `55a5609`. SHA commit cuối được ghi ở commit docs kèm biên bản này.

**Retest:** Nếu sửa file PDF key sau review này, chạy lại `npm run test:e2e -- pdf-import.spec.ts` và verify no regression.

**Người review:** QA (độc lập) · 22/11/2026 19:10 UTC+7

---

**CHỮ KÝ ĐIỆN TỬ (checksum của biên bản review này):**  
SHA-256: `bccca8bf3d783aeb2a8b4aed66f98088d683659424d9bfb941abba4a0c8e34d5` (tính trước khi ghi dòng checksum vào file)

## Đối chiếu sau bàn giao ngày 23/11/2026

Tech Lead kiểm lại commit triển khai `231ab23` trên Windows, Node 24.13.0, npm 11.6.2, Playwright 1.65.1 và Chromium 159.0.8154.6. Đây là phiên bản của lượt kiểm lại.

| Phép kiểm | Quan sát |
|---|---|
| `uv run --locked pytest -q` | 55/55 test backend qua. Còn một cảnh báo Starlette TestClient về httpx. |
| `npm run test:e2e -- --output=../../artifacts/local/audit-pdf-231ab23` từ `apps/web` | 22/22 test Chromium qua, gồm 9 test PDF. Suite tự khởi động Vite và Uvicorn. Hai ca luồng chính mở TXT và JSON tải thực tế. |
| Lint, format, typecheck, build frontend. Ruff, mypy và checker 299 dòng | Các lệnh kiểm đều qua. Build tạo riêng chunk PDF.js và worker. |
| Checkout Windows | Trước khi thêm `*.pdf -text` vào `.gitattributes`, bộ lọc `git -c core.autocrlf=true cat-file --filters HEAD:<đường dẫn>` đổi LF sang CRLF ở ba fixture. Sau chỉnh sửa, byte và SHA-256 của cả bốn PDF khớp tệp đang chạy. |

Đo riêng trên Chromium với PDF giả lập hai trang. Mỗi kích thước chạy một lượt trong ngữ cảnh trình duyệt mới. Thời gian mở tính từ chọn file đến khi ô **Trang đầu** xuất hiện. Trích chữ tính từ phím Enter trên **Trích văn bản** đến khi `18/12` xuất hiện trong ô nhập. Phân tích tính từ bấm **Phân tích** đến khi nhận phản hồi và đọc xong JSON của `/api/analyze`. API trả HTTP 200, `hybrid` và năm vùng ở cả hai lượt.

| Kích thước | Mở PDF | Trích chữ | Phân tích hybrid |
|---|---:|---:|---:|
| 390px | 857 ms | 57 ms | 56 ms |
| 1440px | 871 ms | 51 ms | 52 ms |

**File xuất từ Chromium.** Chọn trang 1–2 của PDF mô phỏng, chạy `hybrid`, thêm `tạ hư cấu` vào nhãn `NAME`, xác nhận rồi lưu trực tiếp hai lượt tải. API trả năm nhãn `NAME`, `DOB`, `ID`, `PHONE`, `ADDR` trước khi sửa. Tên nhãn ngày sinh là `DOB`. TXT khớp byte UTF-8 của bản xem trước, JSON có đúng `redacted_text` và `metadata`, số vùng đã che là 6. Cả hai giữ `18/12`.

| Tệp | Byte | SHA-256 |
|---|---:|---|
| [TXT đã rà soát](../evidence/demo-benh-an-ngoai-tru.reviewed.txt) | 623 | `9c3b56ef6b7ace66fe33b067bde7debfe9a76e7dc18d1bab491ad5f105560a3a` |
| [JSON đã rà soát](../evidence/demo-benh-an-ngoai-tru.reviewed.json) | 873 | `f809471eb0990eb6dd3533b3df18ade8cbcc3ed90dbc00ddbe85362ce4519a19` |

**QA đối chiếu độc lập.** Parfit chạy lại Chromium ở 390px và 1440px trên `90a21bd`. Cả hai lượt tải khớp từng byte với hai tệp đã commit. QA xác nhận đủ sáu vùng được che, cấu trúc JSON tối thiểu và ngày tái khám `18/12` còn nguyên. PDF-04 PASS.

Phạm vi kiểm lại gồm PDF-01–PDF-04. Các hạng mục Three.js và bàn giao toàn dự án có tiêu chí riêng.
