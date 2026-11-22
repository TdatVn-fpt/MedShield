# Review độc lập của Dev — Dashboard G3

**Gate G3: PASS theo quyết định của Lead.** Dev xác nhận dashboard trên bản hợp nhất khớp artifact và các ca sai số liệu, sai ví dụ đã sửa. Phép kiểm cuối phát hiện một dạng số đếm sai kiểu còn có thể làm trắng trang.

Reviewer thực hiện kiểm tra là Dev, độc lập với Lead triển khai dashboard và API. Phạm vi là T302 và phần hiển thị kết quả T303. QA và BA phụ trách kiểm scorer, nội dung đánh giá và kết luận gate.

## Phiên bản đã kiểm

- Nhánh `feat/medshield-demo`. Phép kiểm bắt đầu từ `d18bb967a20682d13a07b109c1835c2920347169` với thay đổi G3 trong working tree. Artifact, dashboard, CSS và controller vẫn có cùng hash sau khi tích hợp vào `7e998b5`.
- Bản hợp nhất [evaluation.json](../../artifacts/evaluation.json) có SHA-256 `5f260460c4290c511fcefa6c432021572f5115015a06e0859ee8929fac837920`.
- [EvaluationPage.tsx](../../apps/web/src/EvaluationPage.tsx) có SHA-256 `f53072ce7722f101d5f4708d13e78c5e176fa097261a878ec4e3b05a306ec787`. [evaluation.css](../../apps/web/src/evaluation.css) có SHA-256 `16901f9bc698b1676d523c9d0cd8b24c108f667cb9d8a521652b1baec0889f11`.
- [controllers.py](../../apps/api/controllers.py) có SHA-256 `e6301079646d8d0457bc518e6ce9f409e9493652fa59ecb5238545709a68e733`.

## Kiểm trình duyệt và kết quả

Mở Vite ở `http://127.0.0.1:5173/` và bắt response thật khi nhấn **Thực nghiệm**. JSON Chromium nhận qua proxy khớp GET trực tiếp tới API cổng 8000. Trên cả 390px và 1440px, các hàng micro và theo nhãn khớp thứ tự, số đếm và tỷ lệ phần trăm hiển thị, với tối đa một chữ số thập phân. Khi mở mục ví dụ lỗi, số mục, mã ghi chú và văn bản giả lập khớp response. Trang không tràn ngang. Ở 390px, sáu bảng cuộn trong khung riêng.

| Đơn vị chấm | Phương pháp | Ghi chú | Vùng vàng | Support micro | TP / FP / FN | Micro-F1 hiển thị | Ghi chú còn FN |
|---|---|---:|---:|---:|---|---:|---:|
| `exact_span_label` | Rules | 20 | 33 | 33 | 1 / 8 / 32 | 4,8% | 15 |
| `exact_span_label` | NER | 20 | 33 | 33 | 12 / 0 / 21 | 53,3% | 12 |
| `exact_span_label` | Hybrid | 20 | 33 | 33 | 13 / 4 / 20 | 52% | 11 |
| `redaction_region` | Presidio | 16 | 32 | 399 | 267 / 237 / 132 | 59,1% | 9 |
| `redaction_region` | Philter UCSF | 16 | 32 | 399 | 341 / 132 / 58 | 78,2% | 12 |
| `redaction_region` | GEMINI pyDeid | 16 | 32 | 399 | 195 / 100 / 204 | 56,2% | 11 |

Trước khi bản hợp nhất xuất hiện, API thật trả `200 unavailable`. Chromium hiển thị **Chưa có kết quả đánh giá.** ở cả hai kích thước, với 0 bảng và 0 cảnh báo lỗi. Test chuyển trạng thái dùng response `unavailable` trong bộ nhớ sau một lần tải artifact thật. Trang mở lại chỉ còn thông báo và không giữ bảng cũ. Khi chặn request bằng Playwright, trang giữ tiêu đề và báo **Chưa kết nối được API đánh giá.**

| Lệnh | Kết quả thực tế |
|---|---|
| `npm run test:e2e -- evaluation.spec.ts --output=../../artifacts/local/g3-dev-playwright` từ `apps/web` | 3 ca Chromium qua trong 7,4 giây. |
| `npm run lint`, `npm run format:check`, `npm run build`, `npm run typecheck` từ `apps/web` | Tất cả exit 0. Vite build 28 module. |
| `.\.venv\Scripts\python.exe -B scripts/check_source.py` từ root | 0 vi phạm. |

## Phát hiện cần xử lý

1. **AC-09 · Thiếu thông tin truy vết trên dashboard.** API đã trả seed, revision/hash dữ liệu, các họ trong split, revision/cấu hình CRF và lệnh tái tạo trong `metadata`. Phép kiểm trên DOM cho thấy các trường này chưa hiện. Trang có nguồn và tổng số ghi chú từng split của tiếng Việt. Cần hiển thị thông tin truy vết từ artifact cho từng nhóm hoặc phương pháp tương ứng. [Hợp đồng API](../api-contract.md#get-apievaluation)
2. **AC-10 · Thiếu kết luận đạt/chưa đạt mục tiêu F1.** Trang nêu ngưỡng 85%, nhưng chưa hiển thị kết quả so với ngưỡng. Bản đã kiểm có ADDR đạt 100% ở NER và hybrid, còn mục tiêu trên đủ năm nhãn chưa đạt. Cần thể hiện kết luận riêng dựa trên F1 gốc và ngưỡng từ artifact. Sáu phương pháp trong artifact hiện đều khả dụng. Khi đọc nhánh engine chưa chạy trong source, tôi thấy UI hiện lý do nhưng chưa đọc lệnh tái hiện của hàng. [Đặc tả](../spec.md)
3. **Artifact sai cấu trúc có thể làm trắng trang.** TestClient thay nội dung đọc bằng fixture trong bộ nhớ chứa một hàng `vi/rules` có `status: "available"`, `micro: {}` và ví dụ có `kind: null`. API trả `200 available`. Phát lại đúng cấu trúc đó qua Playwright khiến Chromium báo lỗi đọc `toUpperCase`, phần tử root rỗng và không có cảnh báo trên UI. Artifact công bố không chứa fixture này. Kiểm hợp lệ các trường số liệu và ví dụ trước khi công bố `available`, đồng thời xử lý an toàn payload lỗi phía trình duyệt.

Biên bản và [test trình duyệt](../../apps/web/e2e/evaluation.spec.ts) là hai file do reviewer viết. Các kiểm tra trên không thay đổi source tích hợp, artifact hoặc kết luận gate.

## Kiểm lại sau cập nhật dashboard

- Chromium ở 390px và 1440px đối chiếu 29 giá trị truy vết từ JSON thật trong mục **Nguồn và cách tái tạo**. Seed, revision train/validation và test, revision và cấu hình CRF, mã họ của các split tiếng Việt và lệnh tái tạo đều hiển thị đúng. Digest SHA-256 của tập test tiếng Việt vẫn vắng trong phần hiển thị.
- Cả ba phương pháp tiếng Việt hiển thị **Mục tiêu micro-F1 85% · Chưa đạt** đúng dữ liệu. Phép thử trong bộ nhớ dùng F1 `0.84999` và `0.85`. Cả hai làm tròn thành 85% khi hiển thị, còn kết luận lần lượt là **Chưa đạt** và **Đạt**. Probe này không thay artifact trên đĩa.
- `npm run test:e2e -- evaluation.spec.ts --output=../../artifacts/local/g3-dev-playwright-retest` qua 3 ca trong 5,8 giây. Kiểm tra `tests/test_evaluation.py -k evaluation_unavailable` qua 3 ca và trượt ca `invalid-metrics-and-example`. API vẫn trả `available` cho artifact sai cấu trúc. Kết luận phạm vi dashboard còn `CHANGES_REQUESTED`.

## Kiểm cuối trên `fdf28f6dc9cc25f11a6deea5840a99ed4aaf427c`

- Chromium ở 390px và 1440px khớp 30 giá trị truy vết, gồm cả SHA-256 của tập test tiếng Việt. Micro-F1 đều **Chưa đạt** ngưỡng 85%. Kết quả số nhãn đạt ngưỡng lần lượt là 0/5 với rules, 1/5 với NER và 1/5 với hybrid. Probe F1 `0.84999` và `0.85` xác nhận phép so dùng giá trị gốc.
- FastAPI TestClient trong tiến trình mới trả đúng artifact thật. Các probe tách riêng micro lỗi, số liệu theo nhãn lỗi, `kind` lỗi và nội dung ví dụ lỗi đều trả HTTP 200 `unavailable`. Tổng cộng 55 test Python và 3 ca e2e qua. Lint, format, build, typecheck web và kiểm source cũng qua.
- **Phát hiện còn mở.** Thay riêng `notes` của một kết quả hợp lệ bằng `{"count":20}` khiến TestClient vẫn trả HTTP 200 `available`. Phát lại payload đó làm Chromium lỗi vì React nhận object thay cho chữ hoặc số. Root rỗng và không có cảnh báo. Có thể tái hiện bằng cách thay trường trong bản sao trong bộ nhớ và đặt `EVALUATION_PATH` bằng mock. Các trường số đếm hiển thị cần được kiểm trước khi trả `available`.
- Lead thông báo G3 PASS và mở G4. Kết quả mô hình và phát hiện còn mở được giữ trong biên bản để theo dõi.
