# Checklist chất lượng đặc tả

Ngày 2026-11-18. Phạm vi: đặc tả yêu cầu, không chứng minh triển khai.

- [x] Nêu nhu cầu và giá trị người dùng.
- [x] Các phần template bắt buộc đã hoàn thành.
- [x] User story có ưu tiên và independent test.
- [x] Có kịch bản Given/When/Then.
- [x] FR001–008 ánh xạ AC01–12.
- [x] Tiêu chí thành công có phép kiểm cụ thể.
- [x] Không còn NEEDS CLARIFICATION.
- [x] Phạm vi/giả định/phụ thuộc rõ ràng.
- [x] Offset và nhãn có nguồn chuẩn duy nhất.
- [x] Có edge cases Unicode/BOM/CRLF/race.
- [x] Có giới hạn input/entities và lỗi riêng tư.
- [x] Có điều kiện xuất và vô hiệu kết quả.
- [x] Có provenance và phép đo trước sửa tay.
- [x] Tách số cũ khỏi số mới và trạng thái upstream.
- [x] Có yêu cầu responsive/keyboard/fallback.
- [x] Không coi điểm F1 thấp là lý do đổi đáp án.

Ghi chú: ràng buộc API/codepoint/stack là yêu cầu kỹ thuật do chủ dự án chỉ định; đặc tả sản phẩm dẫn chiếu hợp đồng chi tiết thay vì tự tạo triển khai. Reviewer QA kiểm tra thêm trước G0 PASS.
