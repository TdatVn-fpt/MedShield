# Kế hoạch triển khai MedShield

## Mục tiêu và giới hạn

Nguyễn Tiến Đạt có thể chạy website trên Windows, nhận diện và rà soát năm nhãn NAME/DOB/PHONE/ID/ADDR, xuất văn bản đã che và bảo vệ phần AI bằng artifact do chính phiên bản này đo. Sản phẩm dùng React + TypeScript + Vite và FastAPI + Python, ưu tiên CPU, không đăng nhập và không lưu bệnh án. Giao diện và tài liệu tiếng Việt; tên biến/hàm/API tiếng Anh.

Kế hoạch không thay phần mềm chạy được. Chỉ bắt đầu triển khai chặng kế khi reviewer độc lập chốt PASS chặng hiện tại. Sáu vai trò được gọi theo lượt phù hợp slot runtime; không chờ đủ ngày lịch nếu điều kiện đã đạt.

## Nhịp ba ngày

| Nhịp | Trọng tâm | Điều kiện ra |
|---|---|---|
| Ngày 1 | G0 ngắn gọn rồi G1: repo, spec/contract, môi trường và luồng web/API/rà soát/xuất thật | Dev chạy skeleton; QA viết được test; sau đó QA mở TXT xuất từ câu chưa có trong demo |
| Ngày 2 | G2 rồi G3: dữ liệu, NER/rules/hybrid, thử upstream và đánh giá độc lập | Engine chính chạy thật; thử từng upstream; điểm exact span tái tạo được trên test đã khóa |
| Ngày 3 | G4 rồi G5: UX, 3D, độ ổn định và bàn giao | Mobile/desktop/keyboard, build và checkout sạch, ZIP, README, slide/demo/Q&A, PR/CI nếu có quyền |

## Đường găng

1. Tech Lead kiểm tra repo/remote thực tế và bảo toàn nội dung có sẵn. DevOps kiểm công cụ, chọn dependency tương thích và smoke trước khi khóa phiên bản.
2. BA chốt entity/offset/API/annotation guide; PM lập board và task. Dev + QA review G0 bằng phép kiểm thực tế.
3. Dev xây baseline và luồng nhập/rà soát/xuất; QA kiểm request trình duyệt thật, sửa nhãn/thêm/xóa, ngày tái khám và kết quả cũ trả muộn.
4. Research kiểm nguồn upstream, model/license/revision; chia họ mẫu trước sinh biến thể. QA giữ test cuối; không dùng test để tinh chỉnh. Thiếu tài liệu đính kèm thì dùng upstream và ghi thiếu nguồn.
5. Research chạy rules/NER/hybrid trên cùng test. QA kiểm scorer bằng tập tính tay rồi chạy lại. Dashboard chỉ đọc artifact thật.
6. Dev hoàn thiện Three.js và UX. DevOps đóng gói CI/Windows/Docker/ZIP. QA và một agent ngoài DevOps chạy hướng dẫn từ checkout sạch. PM đối chiếu từng đầu ra với yêu cầu.

## Tiêu chí điều phối

- Mọi task có ID, user story, tiêu chí, owner, reviewer và đường dẫn bằng chứng tại [tasks.md](tasks.md).
- Source viết tay tối đa 299 dòng/file; comment đường dẫn/mục đích; public/hook/handler/nghiệp vụ có docstring/JSDoc. CI kiểm giới hạn và in tên file/số dòng vi phạm.
- Contract chung dùng offset Unicode code point `[start,end)`. Frontend chuyển đổi UTF-16; không normalize sau khi tính offset. Kiểm emoji, tổ hợp dấu, CRLF, BOM và tên lặp.
- Input chỉ trong bộ nhớ; không log text/identifier, token hoặc secret; JSON xuất chỉ bản đã che và metadata an toàn. Kiểm cả lỗi validation và log lỗi.
- Chỉ dùng dữ liệu giả lập để demo/CI/ảnh; không đưa slide khóa học lên repo. Không dùng 94,7% của demo cũ làm số liệu mới.
- Engine phụ có thể bị chặn thật; phải thử, lưu lệnh/lỗi và phạm vi, không gắn tên upstream cho output mô phỏng.

## Rủi ro và cách xử lý

| Rủi ro | Dấu hiệu cần kiểm | Xử lý được phép |
|---|---|---|
| Python mới không tương thích dependency ML | Cài/smoke không thành công | DevOps chọn Python tương thích trong môi trường riêng; lưu phiên bản và lock sau smoke |
| Model hoặc upstream không tải/chạy được | Lệnh tái hiện và lỗi cụ thể | Tiếp tục việc độc lập; công khai engine unavailable; không giả kết quả |
| Thiếu quyền GitHub | Không thể đọc/push/PR sau kiểm tra | Giữ commit local và ghi lệnh push an toàn; không đổi remote dự án khác, không force push/merge main |
| F1 thấp hoặc nhãn thiếu support | Artifact exact span theo nhãn | Báo trung thực support/lỗi/mục tiêu chưa đạt; không đổi đáp án hoặc bỏ mẫu khó |
| Thiếu input học thuật | Không tìm được đề/slide/research cũ | Research dùng nguồn chính thức, ghi nguồn thiếu; chỉ hỏi chủ dự án nếu cần quyết định học thuật riêng |
| Kết quả rò dữ liệu hoặc request cũ | Kiểm payload xuất/log và ca race | Chặn xuất khi chưa duyệt; invalidate phiên và bỏ response cũ; sửa rồi reviewer kiểm lại |

## Đầu ra cuối cùng

README tiếng Việt với Windows/URL/test/ba lỗi khởi động; sơ đồ Mermaid khớp tên file/hàm; báo cáo số liệu và giới hạn; bảng đóng góp/code tái dùng/Codex hỗ trợ; slide Markdown sáu trang; demo ba phút có sửa lỗi trực tiếp; `docs/defense-qa.md`; ZIP source đã thử giải nén; trạng thái thật Git/PR/CI và ba upstream.

PM chỉ chuẩn bị nội dung của chặng sau khi chặng trước chưa PASS. Số liệu, đường dẫn ZIP, SHA và link PR được điền sau bằng chứng thực tế, không dự đoán.
