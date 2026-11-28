# Tổng quan đề tài MedShield

**Nguyễn Tiến Đạt · Samsung Innovation Campus · Lớp AI-NIC4 · Đề tài số 2**

MedShield nghiên cứu cách nhận diện và che định danh trong ghi chú y tế tiếng Việt để chuẩn bị bản chia sẻ. Đề tài tập trung vào tên người, ngày sinh, số điện thoại, mã định danh và địa chỉ. Người dùng có thể sửa các vùng hệ thống đề xuất rồi xác nhận bản đã che trước khi xuất TXT hoặc JSON.

## Phương pháp và phạm vi

MedShield dùng bộ quy tắc theo ngữ cảnh và mô hình CRF huấn luyện trên dữ liệu giả lập. CRF nhận diện tên người và địa chỉ. Chế độ Hybrid kết hợp kết quả từ hai phương pháp. Trình duyệt hiển thị song song nguyên văn và phần đã che để người dùng rà cả vùng che nhầm lẫn vùng còn sót. [Kiến trúc](architecture.md) · [Đặc tả](spec.md)

## Kết quả chính

Trong phép đo Q2 trên 20 ghi chú tiếng Việt giả lập với 33 vùng vàng, micro-F1 đạt 74,07% với quy tắc, 53,33% với CRF và 84,75% với Hybrid. Hybrid vẫn bỏ sót định danh trong 5/20 ghi chú. Các điểm số phản ánh dự đoán tự động trước khi người dùng rà soát. [Phân tích Q2](phase-q2.md)

## Đọc thêm

- [Giới thiệu dự án và mã nguồn](../README.md)
- [Báo cáo thực nghiệm](experiment.md)
- [Đóng góp](contributions.md) · [Nguồn và giấy phép](../THIRD_PARTY.md)
