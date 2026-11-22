# Kế hoạch nhập PDF bệnh án vào MedShield

- **Chủ dự án:** Nguyễn Tiến Đạt · Samsung Innovation Campus · AI-NIC4
- **Cập nhật:** 22/11/2026 · Asia/Saigon
- **Trạng thái:** Đã triển khai bản đầu, chờ nghiệm thu độc lập PDF-01–PDF-04.

## 1. Kết quả đã có

| Hạng mục | Kết quả và bằng chứng |
|---|---|
| Web chạy cục bộ trên Windows | Vite tại `http://127.0.0.1:5173/`, FastAPI tại `http://127.0.0.1:8000/`. Web nhận văn bản dán hoặc TXT UTF-8, hỗ trợ tối đa 50.000 Unicode code point. [Review G1](reviews/G1.md) |
| Luồng rà soát | Đã kiểm trên Chromium việc tải TXT, phân tích, định vị, thêm/xóa/đổi nhãn, xác nhận và tải TXT/JSON. Sửa input làm mất hiệu lực kết quả cũ. [Review G1](reviews/G1.md) |
| AI và quy tắc | Ba chế độ tiếng Việt `rules`, `ner`, `hybrid` đã chạy. CRF nhận diện `NAME` và `ADDR`. Hybrid kết hợp CRF với quy tắc cho năm nhãn. Ba công cụ tiếng Anh Presidio, Philter UCSF và GEMINI pyDeid đã qua smoke đối chứng. [Review G2](reviews/G2.md) |
| Mẫu demo mô phỏng | File TXT ngoại trú đã chạy qua luồng thật. Hybrid tìm 5 vùng, gồm đủ 5 nhãn. Người rà soát thêm tên bỏ sót `tạ hư cấu`, xuất TXT và kiểm tra `[NAME_2]` cùng ngày tái khám `18/12`. Đây là ca demo chức năng. [TXT mô phỏng](evidence/demo-benh-an-ngoai-tru.txt) |
| Kiểm tra PDF tham chiếu | File Phụ lục XXVIII tải được, có 162 trang. Đã render và đối chiếu trang 61–62 theo thứ tự của trình đọc. Trang 61 là mẫu bệnh án ngoại trú `15/BV-01` với các mục hành chính, lý do vào viện, hỏi bệnh và khám bệnh. Trang 62 là phần tổng kết. Một phép thử cục bộ bằng `pypdf` mất khoảng 0,22 giây để trích chữ hai trang sau khi mở tài liệu. Đây là số đo thử ngoài web và chưa gồm AI, OCR hay thời gian rà soát. [Phụ lục XXVIII](https://storage-vnportal.vnpt.vn/sla-ubnd/4772/vanban/28.-phu-luc-xviii.-mau-benh-an.pdf) |

G0–G3 đã PASS. Tính năng PDF thuộc phạm vi G4 và có biên bản nghiệm thu riêng. Theo dõi các phần khác trong [bảng tiến độ](progress.md).

## 2. Mục tiêu và phạm vi bản đầu

**Luồng mong muốn:** Chọn PDF có lớp chữ → chọn trang cần dùng → xem và kiểm tra phần chữ trích được trong **Văn bản gốc** → phân tích → rà soát → xác nhận → tải TXT hoặc JSON.

- Tạo một PDF bệnh án ngoại trú mô phỏng, khoảng 1–2 trang. Tham khảo trường và bố cục ở trang 61–62, điền dữ liệu giả lập và lưu ở dạng PDF có thể chọn chữ. Ghi rõ trên tài liệu rằng đây là mẫu demo học tập.
- Thêm nút **Nhập PDF** bên cạnh **Tải TXT lên**. Với tệp dài, cho chọn khoảng trang trước khi trích chữ. Giữ cả cách dán văn bản và tải TXT.
- Trích chữ bằng PDF.js trong trình duyệt. Khảo sát `pdfjs-dist` 6.5.438 cho thấy gói dùng giấy phép Apache-2.0 và yêu cầu Node phù hợp với Node 24.13.0 trên máy kiểm thử. Chỉ chốt phiên bản sau khi chạy thử trên Vite. API hiện có chỉ nhận chuỗi văn bản sau khi người dùng bấm **Phân tích**. Kiểm tra chữ tiếng Việt và thứ tự dòng, đặc biệt với bảng nhiều cột. [API `getTextContent()` của PDF.js](https://mozilla.github.io/pdf.js/api/draft/module-pdfjsLib-PDFPageProxy.html)
- Đề xuất giới hạn ban đầu là 10 MiB mỗi tệp và tối đa 10 trang mỗi lượt trích. Giữ giới hạn 50.000 code point của API. Khi vượt giới hạn, hướng dẫn chọn ít trang hơn, tránh cắt ngầm nội dung.
- Bản đầu xuất TXT/JSON theo định dạng hiện tại. OCR PDF scan, xuất bản PDF đã che giữ bố cục, và xác nhận hồ sơ đáp ứng biểu mẫu hành chính là các phạm vi riêng.

## 3. Các bước thực hiện

| ID | Việc cần làm | Người làm / kiểm tra | Bằng chứng nghiệm thu |
|---|---|---|---|
| PDF-01 | Chốt luồng, giới hạn và fixture. Tạo PDF giả lập có tên, ngày sinh, điện thoại, mã bệnh nhân, địa chỉ và ngày tái khám. Chọn trước một vùng để trình diễn thêm thủ công nếu model bỏ sót. | BA và Dev / QA | PDF mẫu, nguồn tham khảo, bản chữ kỳ vọng và danh sách vùng cần che. |
| PDF-02 | Tích hợp PDF.js và worker với Vite. Chỉ tải module khi dùng PDF. Xử lý chọn trang, hủy thao tác, PDF lỗi, PDF khóa mật khẩu và trang thiếu lớp chữ. Khóa phiên bản đã chạy thử và ghi nguồn, giấy phép trong `THIRD_PARTY.md`. | Dev / QA | Build thành công, kiểm tiếng Việt và thứ tự dòng trên đúng PDF demo. Trang scan hoặc thiếu chữ được thông báo rõ. |
| PDF-03 | Kết nối văn bản trích được với luồng nhập hiện tại. Khi áp dụng văn bản mới, xóa vùng che, preview và xác nhận cũ. Nếu người dùng chọn tệp khác hoặc sửa ô nhập, bỏ kết quả trích đến muộn. | Dev / QA | Test browser cho PDF → phân tích → sửa vùng → xác nhận → tải TXT. Luồng TXT vẫn qua hồi quy. |
| PDF-04 | Hoàn thiện hướng dẫn Windows và kịch bản 3 phút. QA chạy độc lập trên Chromium, mở file đã tải và ghi thời gian đọc PDF, phân tích AI theo từng bước. | Dev và PM / QA | Biên bản review, phiên bản được kiểm, lệnh chạy lại, file xuất giả lập và các lỗi còn mở. |

**Ước lượng:** 2–4 giờ làm việc cho PDF có lớp chữ, gồm một mẫu giả lập và kiểm thử luồng chính. Đây là dự kiến, phụ thuộc vào thứ tự trích chữ trên biểu mẫu thật. Nếu biểu mẫu làm sai thứ tự bảng, ưu tiên sửa cách gom dòng cho mẫu đã chọn rồi đo lại. Bắt đầu phần triển khai sau khi G3 PASS và đưa phạm vi PDF vào kế hoạch G4 để review cùng luồng nhập hiện có.

## 4. Tiêu chí chấp nhận

1. **Nhập đúng nội dung.** Chọn PDF mô phỏng và trích đúng trang. Các trường tiếng Việt hiển thị dễ đọc, số và ngày giữ nguyên. Người dùng có thể sửa văn bản trước khi phân tích.
2. **Lỗi có hướng xử lý.** Kiểm PDF scan, file sai định dạng, PDF hỏng hoặc yêu cầu mật khẩu, khoảng trang sai và đầu vào quá giới hạn. Với tệp có cả trang chữ lẫn trang scan, báo rõ trang thiếu chữ. Người dùng phải chủ động đổi phạm vi hoặc chuẩn bị TXT trước khi tiếp tục.
3. **Duyệt và xuất đúng.** Chạy hybrid thật, thêm hoặc đổi một vùng che, xác nhận rồi tải TXT. File khớp bản xem trước và giữ ngày tái khám. JSON chỉ gồm `redacted_text` và `metadata`.
4. **Giữ dữ liệu trong bộ nhớ.** Không gửi tệp PDF gốc lên máy chủ. Không lưu nội dung PDF, tên tệp gốc hoặc văn bản trích ra vào log, localStorage hay telemetry. Chỉ dùng fixture giả lập cho demo và kiểm thử.
5. **Luồng cũ vẫn chạy.** Cả PDF, TXT và dán văn bản đều chạy trên bản build kiểm thử. QA kiểm thêm hai kích thước 390px và 1440px, thao tác bàn phím và tình huống chọn tệp mới trong khi tệp cũ còn đang đọc.

## 5. Kịch bản demo sau khi triển khai

1. Mở `http://127.0.0.1:5173/` và chọn PDF bệnh án ngoại trú mô phỏng.
2. Cho giảng viên xem các trường vừa trích trong ô **Văn bản gốc**. Chọn **Tiếng Việt**, **Kết hợp · hybrid** và bấm **Phân tích**.
3. Sửa một vùng nhận diện nếu ca demo có lỗi đã kiểm chứng. Mở **Bản đã che**, xác nhận rà soát và tải TXT.
4. Mở file TXT để đối chiếu vùng đã thay bằng ký hiệu và ngày tái khám vẫn còn.
