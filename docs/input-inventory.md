# Kiểm kê đầu vào

Kiểm tra ngày 18/11/2026, múi giờ Asia/Saigon.

| Nguồn | Đã kiểm tra | Cách sử dụng |
|---|---|---|
| Attachment `pasted-text-1.txt` | Đọc toàn bộ UTF-8, 11 mục | Yêu cầu hiện hành, thời gian ba ngày |
| Attachment `image-1.png` | Xem ảnh Quick Setup | Chỉ xác nhận URL, không suy ra trạng thái repo |
| `C:\Users\Admin\Downloads\Presidio vs Philter vs PyDeID.html` | Đọc văn bản HTML | Tài liệu nghiên cứu thứ cấp; xác minh upstream riêng |
| `C:\Users\Admin\Downloads\MedShield_SIC_Research.zip` | Liệt kê và đọc các Markdown bằng zipfile | Đề cương, nhãn, thiết kế đánh giá, đối chiếu slide và demo cũ |
| Bộ slide SIC gốc/ảnh đề gốc | Chưa tìm thấy qua tên file trong Downloads/Documents/attachments | Bảng đối chiếu slide trong ZIP là nguồn thứ cấp, chưa xác minh lại số trang |

Không sao chép slide khóa học hay toàn bộ ZIP vào Git. Tài liệu ZIP nói ba tuần; yêu cầu hiện hành ba ngày được ưu tiên. Demo HTML cũ nằm trong ZIP, không phải mã nguồn của phiên bản React/FastAPI mới. Số 94,7% của demo cũ, 6 đoạn không được dùng làm kết quả mới.

## Kiểm tra Git thực tế

- Thư mục làm việc ban đầu `D:\Workspace\MedShield` trống, không thuộc repository Git nào.
- `git ls-remote https://github.com/TdatVn-fpt/MedShield.git` không có refs; GitHub API báo size 0, default branch main, quyền push true.
- Khởi tạo baseline main `6e227b0`, push thành công; làm việc trên `feat/medshield-demo`.
- Không có code hoặc thay đổi cũ bị ghi đè, không đổi origin của dự án khác.

## Spec Kit và kỹ năng

- Đọc upstream GitHub Spec Kit; chạy `specify init --help`.
- CLI upstream revision `59d61c59630c3bd5a294f4c23e43a60d8ab98d02`, phiên bản tự báo `1.4.3.dev0`.
- Init Codex/PowerShell trong staging riêng để xem nội dung trước khi copy hạ tầng `.specify` và `.agents` vào checkout. Không dùng force ghi đè constitution do BA sở hữu.
- Đã chạy resolver constitution-template và spec-template thành công. Tiếp tục workflow specify → plan → tasks → analyze → implement với tài liệu dự án.
- Skill Sites dùng chế độ local-only, theo stack người dùng chỉ định. Không đăng ký/publish Sites.
- Tìm trong các thư mục skill người dùng không thấy skill chuyên UI/UX hoặc Three.js. Dùng tài liệu Three.js chính thức và kỹ thuật React/TypeScript; ghi nguồn trong research.

## Giới hạn học thuật cần công khai

Dữ liệu giả lập do agent tạo/kiểm là dữ liệu của dự án, không phải benchmark lâm sàng. Chưa có xác nhận chủ dự án trực tiếp rà soát mẫu nào. Việc giảng viên chấp nhận dữ liệu giả lập và mô hình NER nhẹ cần được chủ dự án xác nhận trước buổi bảo vệ; lựa chọn triển khai hiện tại không được trình bày như quyết định của giảng viên.
