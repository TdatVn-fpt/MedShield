# Kế hoạch QA độc lập

Tác giả: subagent QA. Nguồn yêu cầu: `docs/spec.md`, `docs/api-contract.md`, `docs/annotation-guide.md`, constitution và lệnh triển khai đính kèm. Đây là thiết kế kiểm tra; chưa chứng minh chức năng sau G0 đã chạy.

## G0 — khả năng kiểm thử

- Đọc hợp đồng và parse mọi JSON minh họa; tính lại slice NAME/DOB/ID và giữ ngày hẹn.
- Tự build/typecheck, lint, formatter web skeleton; chạy health TestClient, lint/typecheck/source limit backend sau khi môi trường có sẵn.
- Kiểm tra owner/reviewer/dependencies, tính thống nhất story IDs, giới hạn và lỗi đủ xác định đầu ra.

## G1 — web/API/rà soát/xuất

1. Nhập câu mới do QA viết, phân tích qua request HTTP thật, xác nhận substring và ngày hẹn còn nguyên.
2. Xóa một phát hiện, đổi nhãn một phát hiện, chọn thêm đoạn sót; preview khớp danh sách hiện hành.
3. Xuất bị khóa trước xác nhận; tải TXT rồi mở, so byte UTF-8/nội dung với preview. JSON chỉ `redacted_text`, `metadata`.
4. Sửa input và entity sau xác nhận: khóa xuất ngay. Làm chậm response analyze/redact cũ rồi trả sau request mới: không phục hồi kết quả cũ.
5. API từ chối rỗng/quá dài, extra fields, malformed JSON, float/bool offsets, negative/end overflow/overlap/duplicate, label/score sai; response/log không có input canary.
6. Token cùng nhãn và exact slice tái dùng; tài liệu mới reset; xóa span không tự thêm lại.

## G2 — dữ liệu và model

QA sở hữu tập test cuối, khóa hash trước chạy test; Research chỉ điều chỉnh train/validation. Chia family trước sinh biến thể; kiểm trùng văn bản và giao family giữa splits. Dữ liệu agent sinh/kiểm ghi đúng provenance; human review chưa xác nhận là 0.

Kiểm Unicode: emoji trước entity, tên NFD, CRLF, BOM qua file nhập, tên lặp và selection UTF-16 sang code point. Mỗi upstream tự smoke bằng môi trường khai báo, đối chiếu revision/license/nguồn; lỗi cài/chạy phải có lệnh và quan sát, không mô phỏng output.

## G3 — scorer và tái tạo

Tập tính tay gồm một exact match (TP1), sai nhãn (FP1/FN1), sai biên (FP1/FN1), dư (FP1), sót (FN1): tổng TP1/FP3/FN3, P=R=F1=0,25. Dùng thêm mẫu âm và nhãn support0. QA tự chạy scorer trên tập này rồi chạy lại rules/NER/hybrid trên cùng test khóa. Đối chiếu artifact với dashboard, support, số ghi chú còn FN và lỗi thật. Tách đơn vị vùng che/nhãn và ngôn ngữ.

## G4 — UX và độ ổn định

Kiểm desktop1440px/mobile390px, không cuộn ngang trang; Tab/Enter/Space/focus; nhãn chữ+màu và tương phản. Lazy Three.js chỉ tải khi mở, reduced motion, dọn renderer/tài nguyên/listeners khi rời; WebGL/module lỗi có hình thay thế và review/export vẫn chạy. Lặp nghiệp vụ thêm/xóa/đổi nhãn/xuất sau lỗi.

## G5 — bàn giao

QA cùng agent ngoài DevOps dùng checkout sạch theo README trên Windows: setup, mở web, câu mới, sửa/xuất TXT, đánh giá lại. Kiểm CI thật (job skip không là smoke PASS), ZIP loại secrets/.git/dependencies và giải nén đọc README. Đối chiếu tài liệu với artifact/engine/SHA/PR/ZIP hiện hành. Mỗi gate có `docs/reviews/Gx.md` kèm phiên bản, lệnh/thao tác, kỳ vọng/quan sát và lỗi/retest.
