# G2 — Review gán nhãn tập test tiếng Việt

**PASS phạm vi gán nhãn.** QA soạn bộ `vi-test-v1`, BA (Codex) rà soát độc lập theo [hướng dẫn gán nhãn](../annotation-guide.md). Kết luận áp dụng cho [test.jsonl](../../data/test.jsonl) có SHA-256 `ad2dce2254e1eac809df51f5a827f64bfdb425babf1ca56cb5db87f7dea9bb96` theo quy tắc trong [manifest của QA](../../data/test-manifest.json).

BA đọc `note_id`, `family_id` và `text` trước, tự xác định nhãn và giá trị cần che. Sau đó chạy Python qua `.\.venv\Scripts\python.exe -B -` để tính khoảng code point `[start,end)` từ chuỗi gốc, đối chiếu từng tuple với nhãn QA và tính lại SHA-256 sau khi chuyển CRLF phân cách dòng về LF. Cả 20/20 ghi chú khớp hoàn toàn, gồm 33 vùng và 5 ghi chú âm. Sáu họ và danh sách ID trong từng họ khớp manifest.

| Nhãn | Số vùng |
|---|---:|
| NAME | 17 |
| DOB | 4 |
| PHONE | 4 |
| ID | 5 |
| ADDR | 3 |

- Các ca đính chính giữ cả giá trị cũ và mới khi cả hai đều định danh người bệnh. Tên xuất hiện nhiều lần có span riêng. Chức danh và từ dẫn nằm ngoài span.
- Các ca Unicode dùng đúng khoảng trên nguyên bản có emoji, tên có dấu tổ hợp và địa chỉ nhiều dòng. Địa chỉ giữ dấu chấm viết tắt, dấu phẩy nội bộ và CRLF thuộc giá trị.
- Số lưu kho, số niêm phong, mã thiết bị, lô thuốc, ICD, giờ và ngày tái khám giữ nguyên theo ngữ cảnh. Ba địa chỉ được gán đều là địa chỉ cư trú.

Không có yêu cầu sửa nhãn ở revision này. QA tiếp tục giữ bộ test khóa và kiểm giao họ với train/validation trong review split. Tái kiểm này chỉ dùng văn bản giả lập và nhãn vàng, chưa chạy engine hoặc tính điểm. Số mẫu do người học trực tiếp rà soát đã xác nhận là 0.
