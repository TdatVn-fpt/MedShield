# MedShield Constitution

Version: 1.0.0. Ngày thông qua dự kiến: 18/11/2026. Trạng thái G0: READY_FOR_REVIEW (BA soạn; Dev/QA kiểm tra). Chủ dự án Nguyễn Tiến Đạt, SIC AI-NIC4.

## I. Trung thực thực nghiệm

Engine và NER chỉ được công bố đã chạy khi có smoke test và bằng chứng thực tế. Không mô phỏng output dưới tên Presidio/Philter/pyDeid. Mọi điểm trên web lấy từ artifact script tạo, có seed, revision, dataset split và lệnh tái tạo. Dự đoán được chấm trước sửa tay. Phân biệt chất lượng mô hình và tính đúng quy trình; không sửa test để vượt gate. Điểm demo cũ không được dùng cho phiên bản mới.

## II. Bảo vệ dữ liệu

Chỉ demo/CI/tài liệu bằng dữ liệu giả lập có provenance. Xử lý input và token map trong bộ nhớ, không log/lưu localStorage/telemetry/commit hoặc đưa vào artifact. Lỗi validation và lỗi engine không được lộ input. JSON xuất chỉ có bản che và metadata tối thiểu. Người dùng phải rà soát và xác nhận trước tải.

## III. Một hợp đồng duy nhất

Năm nhãn NAME/DOB/PHONE/ID/ADDR theo `docs/annotation-guide.md`; Entity/API theo `docs/api-contract.md`. Offset code point `[start,end)`; không normalize nguyên bản sau tính vị trí; spans cuối không chồng lấn. Mọi sửa input/entities vô hiệu preview/xác nhận cũ; response cũ không được ghi đè phiên bản mới. Token lặp dựa `(label, slice chính xác)`, đánh số lại mỗi tài liệu.

## IV. Mã dễ giải thích và kiểm chứng

React + TypeScript + Vite, FastAPI + Python, kiến trúc router/controller → schema → service → adapter; React view và state hook tách trách nhiệm. Mỗi source viết tay Python/JS/TS/JSX/TSX/CSS/test tối đa 299 dòng vật lý, có comment đầu file ghi đường dẫn/mục đích. Hàm nghiệp vụ, handler, export và hook có docstring/JSDoc nêu tên, hành vi, input/output. Không nén câu lệnh để lách giới hạn. Bật lint/typecheck/formatter; khóa dependency sau smoke; lưu nguồn/revision/license trong THIRD_PARTY.md.

## V. Review độc lập theo chặng

G0–G5 dùng TODO → IN_PROGRESS → READY_FOR_REVIEW → PASS; lỗi dùng CHANGES_REQUESTED, trở ngại tái hiện được dùng BLOCKED. Tác giả không tự PASS. Reviewer đọc sản phẩm/diff và chạy ít nhất một kiểm tra liên quan, lưu `docs/reviews/Gx.md`. Chỉ chuyển chặng sau PASS tích hợp; sửa code đã PASS phải mở lại phạm vi tương ứng. Một file chỉ một người sửa tại một thời điểm; thiếu slot thì xếp lượt sáu vai trò, không giả review độc lập.

## VI. Chạy lại được trên Windows

README tiếng Việt ghi lệnh PowerShell, URL, test và khắc phục lỗi. CI kiểm tra lint, typecheck, 299 dòng, backend tests, frontend build và browser sửa → xuất. Lazy Three.js có reduced motion, cleanup và static fallback. Giao diện hoạt động 390px và 1440px với bàn phím. ZIP loại secrets/.git/dependencies/model không được phép phân phối, được giải nén kiểm tra. Git feature branch, commit nhỏ, không force-push/merge main; draft PR nếu có quyền.

## Quản trị thay đổi

Tech Lead phân xử theo spec/bằng chứng. Thay đổi hợp đồng phải cập nhật spec, test, task và reviewer liên quan; thay đổi chính sách nhãn/split cần revision đánh giá mới. Nguyên tắc mới không được giảm yêu cầu trung thực, quyền riêng tư hoặc bỏ qua review. Trạng thái thực tế xem `docs/progress.md`, không suy PASS từ văn bản constitution này.
