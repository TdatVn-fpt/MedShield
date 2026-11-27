# Đóng góp và nguồn tái sử dụng

Chủ dự án: Nguyễn Tiến Đạt, Samsung Innovation Campus AI-NIC4. Codex hỗ trợ triển khai và kiểm tra qua sáu vai trò agent; đây là hỗ trợ AI, không phải sáu thành viên con người. Chưa ghi nhận chủ dự án trực tiếp rà soát mẫu dữ liệu mới.

| Phần | Nguồn tái sử dụng | Đóng góp của phiên bản MedShield |
|---|---|---|
| Web/API | React, TypeScript, Vite, FastAPI, Pydantic | Luồng rà soát, hợp đồng năm nhãn, chuyển Unicode, chặn response cũ, xác nhận và xuất đúng quyết định |
| Quy tắc | Python regex; nghiên cứu thiết kế từ tài liệu đã dẫn | Các pattern ngữ cảnh tiếng Việt; giải quyết chồng lấn; giữ ngày tái khám |
| NER | sklearn-crfsuite/python-crfsuite | Dữ liệu giả lập có nhãn, đặc trưng, huấn luyện, adapter và thí nghiệm riêng; kết quả thực ở artifact sau G3 |
| Ba công cụ Anh ngữ | Presidio, Philter UCSF, GEMINI pyDeid | Chuẩn hóa đối chứng cùng input và công khai trạng thái; không nhận thuật toán upstream là do chủ dự án tự viết |
| Hướng dẫn và đánh giá | Tài liệu SIC được trích qua bảng đối chiếu cũ; tài liệu upstream | Áp dụng exact span+label, split theo họ, test do QA giữ, phân tích lỗi và bằng chứng chạy lại |
| Nhập PDF | PDF.js, ReportLab | Trích chữ theo trang ở trình duyệt, quản lý tác vụ cũ, PDF ngoại trú giả lập và kiểm tra file xuất |
| Quy trình | GitHub Spec Kit, uv/npm, Playwright | Đặc tả, kiểm tra theo chặng, lệnh Windows và tái tạo. Three.js, GitHub Actions và ZIP nộp toàn dự án còn trong kế hoạch. |

Phiên bản, revision, giấy phép: [THIRD_PARTY.md](../THIRD_PARTY.md). Không dùng lại số 94,7% của demo cũ làm số bản mới. Khi bảo vệ, trình bày những phần đã đọc và hiểu bằng lời của mình; mức đóng góp triển khai có Codex hỗ trợ cần được nói rõ.
