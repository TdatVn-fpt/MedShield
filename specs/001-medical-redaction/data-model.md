# Mô hình dữ liệu

Ràng buộc trường chuẩn chỉ định nghĩa tại [hợp đồng API](../../docs/api-contract.md). Tệp này tạo điểm dẫn chiếu ổn định cho tasks, không nhân bản giới hạn.

- `AnalyzeRequest.text`, `.language`, `.mode`: mục request analyze.
- `Entity.start`, `.end`, `.label`, `.source`, `.score`: mục kiểu Entity.
- `RedactRequest.entities`: request redact và kiểm tra chồng lấn.
- `RedactResponse.redacted_text`, `.metadata`: đầu ra redact.
- `Engine.name`, `.status`, `.mode`, `.language`: metadata engine.

Trạng thái: sửa input hủy entities/preview/xác nhận; analyze tạo kết quả hiện hành; sửa entity hủy xác nhận và chờ preview; redact thành công cho preview mới; người dùng xác nhận mới bật xuất. Mọi response có revision cũ bị bỏ qua.
