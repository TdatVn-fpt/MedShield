# G1 — Review nghiệp vụ BA

- Reviewer: BA `/root/ba`; độc lập với tác giả API (Tech Lead `/root`) và web (Dev).
- Phạm vi: đọc router, schemas, service analyze/redact, rules và error middleware; tự chạy FastAPI TestClient để kiểm tra ý nghĩa chỉnh sửa và response dùng cho xuất.
- Phiên bản: base commit `898457710bd4901c7339b05f64d861c0419c3a58`, working tree G1 chưa commit. SHA-256 từng file API đã đọc/chạy được lưu tại [G1-ba-results.json](G1-ba-results.json). Sửa API sau thời điểm này phải mở lại phần bị ảnh hưởng.
- Kết luận phạm vi API: **PASS**, 20/20 phép kiểm tự chạy.
- Kết luận nghiệp vụ G1: **PASS**, gồm API và đối chiếu file tải thực tế từ QA. QA chịu trách nhiệm kết luận phần thao tác/browser và Tech Lead tổng hợp gate; BA không giả nhận đã tự điều khiển trình duyệt.

## Cách kiểm và kết quả

Lệnh thực thi: `$OutputEncoding = [System.Text.UTF8Encoding]::new($false)` rồi Python script qua stdin với `@' ... '@ | .\.venv\Scripts\python.exe -`. Script import `fastapi.testclient.TestClient`, `apps.api.main.app`, tạo client với `raise_server_exceptions=False` và gửi POST JSON thật trong ASGI app. Đây là kiểm tra API in-process, không phải request trình duyệt tới backend live.

| Tiêu chí | Thao tác/kỳ vọng | Quan sát thực tế |
|---|---|---|
| AC-03/04, mẫu chuẩn | Analyze câu `Người bệnh Mai An, sinh ngày 03/02/1995, mã BN-00071. Hẹn khám lại 18/12.` | HTTP 200; NAME `[11,17)`, DOB `[29,39)`, ID `[44,52)`; preview đúng contract; giữ `18/12` |
| Năm nhãn trên câu ngoài demo | Analyze tên viết thường, DOB, HS ID, phone và địa chỉ chứa `TP.` | HTTP 200; năm slices khớp gold tự viết; địa chỉ đầy đủ, không cắt tại `TP.`; giữ `20/12` tái khám |
| AC-05/06, xóa | Bỏ entity DOB khỏi kết quả mẫu chuẩn rồi `/api/redact` | Chỉ `03/02/1995` được giữ lại; NAME/ID vẫn che; không tự nhận diện lại DOB |
| AC-05/06, đổi nhãn | Đổi NAME thành ADDR/source manual/score 1 rồi redact | Token thành `[ADDR_1]`, counts NAME=0 ADDR=1, DOB=1 ID=1 PHONE=0 |
| AC-05/06, thêm | Thêm span `Hoa Xuân` vào `Ghi chú thử: Hoa Xuân cần theo dõi. Tái khám 18/12.` | Chỉ đúng span được thay NAME_1, phần còn lại giữ nguyên |
| Danh sách duyệt rỗng | Gửi `entities: []` | Text nguyên vẹn; server không áp quy tắc lại |
| AC-08, token lặp | Gửi spans đảo thứ tự cho `🙂 Mai An gặp Mai An; mai an hỗ trợ.` | `🙂 [NAME_1] gặp [NAME_1]; [NAME_2] hỗ trợ.`; counts NAME=3, không nhầm với số token duy nhất |
| AC-08, reset tài liệu | Gửi tài liệu kế tiếp với một tên khác | Bắt đầu lại `[NAME_1]` |
| Unicode | Redact tên NFD trong text có emoji và CRLF | Đúng span; emoji/CRLF và nội dung ngoài span giữ nguyên |
| AC-07, JSON tối thiểu | Kiểm tra keys response redact và metadata | Chỉ `redacted_text,metadata`; metadata chỉ count/counts/offset_unit; không có chuỗi tên đã chọn hoặc bản đồ token |
| Validation an toàn | Offset âm/rỗng/vượt cuối/float/bool, nhãn lạ; span trùng | HTTP 422 envelope `error`; không trả tên/text input. Span trùng dùng `INVALID_SPAN` |
| Engine chưa khả dụng | Analyze mode ner ở G1 | HTTP 503 `ENGINE_UNAVAILABLE`; không fallback regex gắn tên NER |
| JSON hỏng | Body `{broken SECRET_SENTINEL` | HTTP 422 envelope an toàn; không lộ sentinel |
| Không cache | Kiểm header response analyze | `Cache-Control: no-store` |

Toàn bộ danh sách kiểm và kết quả machine-readable nằm trong `G1-ba-results.json`: 20 PASS, 0 FAIL.

## Ca ngoài demo để tái hiện

```text
Bệnh nhân nguyễn minh hà, sinh ngày 14/07/1987, mã HS-08092; điện thoại 0912345678; địa chỉ: 12 đường Sen, phường Bình An, TP. Thủ Đức. Hẹn tái khám 20/12.
```

Gửi `/api/analyze` với `language: "vi", mode: "rules"`. Preview mong đợi và đã quan sát:

```text
Bệnh nhân [NAME_1], sinh ngày [DOB_1], mã [ID_1]; điện thoại [PHONE_1]; địa chỉ: [ADDR_1]. Hẹn tái khám 20/12.
```

Đoạn kiểm tối thiểu có thể chạy lại từ root bằng `.\.venv\Scripts\python.exe`:

```python
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app, raise_server_exceptions=False)
text = "Người bệnh Mai An, sinh ngày 03/02/1995, mã BN-00071. Hẹn khám lại 18/12."
response = client.post("/api/analyze", json={"text": text, "language": "vi", "mode": "rules"})
assert response.status_code == 200
entities = response.json()["entities"]
assert [(e["start"], e["end"], e["label"]) for e in entities] == [
    (11, 17, "NAME"), (29, 39, "DOB"), (44, 52, "ID")
]
reviewed = [e for e in entities if e["label"] != "DOB"]
export = client.post("/api/redact", json={"text": text, "entities": reviewed}).json()
assert export["redacted_text"] == (
    "Người bệnh [NAME_1], sinh ngày 03/02/1995, mã [ID_1]. Hẹn khám lại 18/12."
)
assert set(export) == {"redacted_text", "metadata"}
```

## Bổ sung: đối chiếu download trình duyệt thực tế

QA báo hai browser tests PASS và cung cấp `artifacts/local/G1-reviewed.txt`, `artifacts/local/G1-reviewed.json`. BA đã tự đọc cả hai và chạy Python asserts độc lập, không chỉ đọc kết luận QA.

Quyết định rà soát được kiểm: câu giả lập mới có `Đỗ Minh Lâm`, ngày sinh `12/04/1988`, mã `BN-90412`, nội dung `Ho khan hai ngày`, hẹn `23/12`; người dùng đổi NAME sang ADDR, thêm `Ho khan` làm NAME và xóa ID. Vì vậy mã còn nguyên là đúng quyết định người dùng, không phải lỗi rò rỉ span còn được duyệt.

TXT đã đọc UTF-8 có đúng toàn bộ nội dung sau (không thừa newline cuối):

```text
Người bệnh [ADDR_1], sinh ngày [DOB_1], mã BN-90412. [NAME_1] hai ngày. Hẹn khám lại 23/12.
```

JSON có đúng hai trường `redacted_text` và `metadata`; text bằng TXT. Metadata entity_count=3; counts NAME=1, DOB=1, ADDR=1, PHONE=0, ID=0; offset_unit=`unicode_code_point`. Cả hai file không chứa tên gốc, ngày sinh gốc hoặc `Ho khan`; vẫn chứa mã đã bỏ che và ngày tái khám theo quyết định.

Lệnh đọc/hashing đã chạy: `Get-Content -Encoding UTF8 artifacts/local/G1-reviewed.txt`, tương tự JSON; `Get-FileHash ... -Algorithm SHA256`; Python stdin qua `.\.venv\Scripts\python.exe -` đọc `Path.read_text(encoding='utf-8')`, kiểm equality TXT/expected, keys JSON, metadata exact, absence các chuỗi đã che và presence mã/tái khám. Kết quả: **PASS**.

| File tải thực tế | SHA-256 |
|---|---|
| `artifacts/local/G1-reviewed.txt` | `a2647bf9b82f44fdc5a0574464018c7e572db7c5b4c48f1876da7b9b61d3affa` |
| `artifacts/local/G1-reviewed.json` | `32e04159c54c78c4ecc711f15ff22aaf408bf5bca0bf43bcd2c13b5503c8ba09` |

Các file local là bằng chứng từ dữ liệu giả lập, có thể bị loại khỏi Git/ZIP; bản ghi hashes và nội dung mong đợi ở đây giữ việc đối chiếu có thể kiểm tra. Không có lỗi mở trong phạm vi BA G1.

## Giới hạn review

- BA tự kiểm API và file download; phần điều khiển UI thêm/xóa/đổi nhãn/xác nhận, invalidation input, stale response và export gating qua browser do QA kiểm và ghi biên bản riêng.
- TestClient in cảnh báo deprecation Starlette/httpx, nhưng các request đều chạy thành công. Đây không phải bằng chứng lỗi nghiệp vụ; DevOps xem tương thích trong lockfile.
- Không có lỗi nghiệp vụ API mới cần sửa trong 20 ca. Baseline có thể bỏ sót ngoài ca này; chất lượng nhận diện tổng thể phải chờ G2/G3 đo trên dữ liệu khóa, không dùng 20 ca này làm điểm AI.

## Tái kiểm BA ngày 21/11/2026

Codex thực hiện vai trò BA, đối chiếu T102/T103 và bốn sửa đổi API của Dev trên working tree G1 tại base `898457710bd4901c7339b05f64d861c0419c3a58`. Kết quả mục này dựa trên request và file tải tự kiểm. Bản ghi Claude và [JSON kết quả lịch sử](G1-ba-results.json) được giữ nguyên. So với mã băm lịch sử, năm file API đã đổi. Tiền tố SHA-256 tại lần chạy là `7daa7ca42142` cho `adapters/rules.py`, `fef3920d3ddc` cho `controllers.py`, `39c0390e2d91` cho `main.py`, `c0dcfc6d7dd0` cho `schemas.py` và `be56bf555469` cho `services/analysis.py`.

Chạy `.\.venv\Scripts\python.exe -B -m uvicorn apps.api.main:app --host 127.0.0.1 --port 18001 --no-access-log`. Gửi HTTP bằng `urllib.request`. Chạy Chromium headless bằng script Playwright qua `node -` trong `apps/web`, với Vite cổng 15173 proxy sang API trên. Theo dõi body request và response thực, đọc file download từ thư mục tạm của Playwright.

| Phạm vi | Quan sát khi tái kiểm |
|---|---|
| `/health` và `/api/analyze` | `/health` trả 200, có sáu cặp duy nhất. `vi/rules` và `en/rules` đều phân tích thật, trả 200 và metadata engine trùng từng mục health. Bốn cặp `ner`/`hybrid` trả 503 `ENGINE_UNAVAILABLE`. |
| Giới hạn kết quả | Với 2.000 lần lặp số điện thoại giả lập, analyze trả đủ 2.000 vùng, dùng `[PHONE_1]` nhất quán. Redact nhận toàn bộ danh sách, trả cùng bản che và đếm 2.000 vùng. Với 2.001 lần lặp, analyze trả 422 `VALIDATION_ERROR`, `Cache-Control: no-store` và chỉ có envelope `error` với thông báo chia nhỏ văn bản. |
| UTF-8 lỗi và vùng rỗng | Hai chuỗi byte UTF-8 lỗi ở mỗi endpoint analyze/redact đều trả 422 `VALIDATION_ERROR` và envelope tối thiểu, không lặp chuỗi đánh dấu. Ca vi/en với cụm dẫn tên theo sau bởi khoảng trắng và dấu phẩy giữ nguyên cụm đó, nhận diện đúng tên hợp lệ ở câu tiếp theo. |
| AC-05/06/07, quyết định và file xuất | Ở 1440px và 390px, đổi NAME sang ADDR, thêm `Ho khan` thành NAME với `manual`/`1`, xóa ID. Request redact cuối chứa đúng ba vùng đã duyệt. Preview giữ mã đã bỏ che và ngày hẹn; tên, ngày sinh và đoạn vừa thêm đều được che. Cả hai nút tải bị khóa trước xác nhận và bị khóa lại khi sửa vùng hoặc đổi input. TXT/JSON tải ở cả hai kích thước trùng từng byte với hai bản lưu trong `docs/evidence` và `artifacts/local`, khớp SHA-256 ở trên. JSON đúng hai trường, có đủ năm bộ đếm và `offset_unit`. |
| AC-02/04/06, Unicode và phản hồi muộn | Chọn thủ công tên dạng tổ hợp sau emoji, xác minh offset code point trên request và giữ CRLF trong preview khi tải TXT có BOM trên trang mới. Nhập sẵn ghi chú rồi bấm `Tải TXT lên` và chọn file cũng giữ CRLF. Phản hồi analyze cũ sau analyze mới và phản hồi redact cũ sau đổi nhãn lần nữa đều không ghi đè kết quả mới. |
| Kích thước và WebGL | Hai kích thước không cuộn ngang và hoàn thành luồng xuất khi Chromium tắt WebGL. Minh họa 3D và hình thay thế thuộc phạm vi G4. |

Lưu ý cho QA khi dựng ca CRLF. Sau khi điền textarea, gọi thẳng `setInputFiles()` khi textarea còn focus khiến request gửi LF. Dùng thao tác bấm `Tải TXT lên` rồi `filechooser.setFiles()` giữ được CRLF trên cùng ca kiểm. Hai đường này đã được kiểm riêng trên cùng API.

Ruff lint/format và mypy chạy trên `apps/api scripts tests` đều đạt. `python -B -m pytest -q -p no:cacheprovider` đạt 28/28, có một cảnh báo deprecation TestClient/httpx. `python -B scripts/check_source.py` báo `0 violation(s)` ở lần chạy lại. Trong `apps/web`, `npm.cmd run lint`, `typecheck`, `format:check` và `build` đều đạt ở lượt sau sửa. Kết quả browser trong mục này từ kịch bản tái kiểm BA.

**Bàn giao QA và Tech Lead.** Bốn sửa đổi API và luồng quyết định rà soát/xuất đã tái kiểm đạt. QA dùng kết quả này cùng biên bản kiểm thử của mình. Tech Lead tổng hợp trạng thái gate G1.
