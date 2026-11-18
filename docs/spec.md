# Đặc tả MedShield — G0

Trạng thái: READY_FOR_REVIEW. Tác giả: BA. Reviewer: QA (khả năng kiểm thử), Dev (khả năng triển khai). Đây là đặc tả, chưa phải bằng chứng chức năng đã chạy.

## Mục tiêu và phạm vi

Nguyễn Tiến Đạt, SIC AI-NIC4, dùng ứng dụng để chuẩn bị trích đoạn ghi chú y tế giả lập cho học tập/nghiên cứu. Một phiên gồm nhập → phân tích → rà soát/sửa → xem trước → xác nhận → xuất. Giao diện và tài liệu tiếng Việt; tên code/API tiếng Anh. Chạy CPU cục bộ trên Windows bằng React + TypeScript + Vite và FastAPI; không cần đăng nhập hoặc cơ sở dữ liệu bệnh án.

## Chuẩn dùng chung

- Entity, giới hạn, lỗi và API: [api-contract.md](api-contract.md).
- Năm nhãn và ranh giới: [annotation-guide.md](annotation-guide.md).
- `start` bao gồm, `end` loại trừ, đơn vị Unicode code point. Không normalize nội dung sau khi tính vị trí. Các entity cuối cùng không chồng nhau.
- API chỉ xử lý trong bộ nhớ. Không lưu input, bản đồ token hoặc định danh gốc vào log, telemetry, localStorage hoặc artifact. Artifact đánh giá chỉ dùng dữ liệu giả lập được phép chia sẻ.
- Xác nhận rà soát là trạng thái giao diện, không phải chứng nhận đã loại bỏ mọi thông tin nhạy cảm. Mọi thay đổi text/entity làm mất xác nhận và bản xuất cũ.

## User stories và tiêu chí chấp nhận

### US-01 — Nhập ghi chú

AC-01: Người dùng dán text hoặc chọn TXT UTF-8 (kể cả BOM), hoặc nạp ví dụ giả lập một lần bấm. TXT lỗi UTF-8 có thông báo dễ hiểu; không gửi chuỗi giải mã lỗi đến API. Bỏ BOM đầu file trước khi tạo input; sau đó giữ nguyên text đang hiển thị. Text chỉ có khoảng trắng không được phân tích. Giới hạn 50.000 code point; quá giới hạn bị từ chối rõ ràng.

AC-02: Sửa đầu vào hủy entities, preview, xác nhận và khả năng xuất ngay. Mỗi phân tích gắn phiên bản input; response về muộn của phiên bản cũ không được ghi đè phiên bản mới, kể cả khi người dùng đã phân tích lần nữa.

### US-02 — Phân tích và đọc phát hiện

AC-03: Nút Phân tích gửi request thật tới `/api/analyze`. Giao diện thể hiện rỗng, đang chạy, thành công, lỗi và engine chưa khả dụng. API phản ánh đúng engine đã chạy, không gắn tên upstream cho regex mô phỏng. Chế độ không khả dụng trả lỗi rõ ràng; không âm thầm dùng engine khác.

AC-04: Kết quả tô đúng substring theo offset, có nhãn chữ và nguồn phát hiện. Bấm entity định vị đoạn tương ứng bằng focus hoặc cuộn nhìn thấy. Emoji trước tên, ký tự tổ hợp, CRLF và xuống dòng phải giữ vị trí đúng. Không dùng màu làm dấu hiệu duy nhất.

### US-03 — Rà soát thủ công

AC-05: Người dùng đổi nhãn, xóa phát hiện sai, chọn một đoạn text gốc và thêm entity bị sót với một trong năm nhãn. Không cho thêm đoạn rỗng, ngoài text hoặc chồng lấn; hiển thị lý do. Entity thủ công có `source: "manual"`, `score: 1`; đây là quyết định người dùng, không tính là dự đoán AI.

AC-06: Preview cập nhật theo chính danh sách người dùng đã duyệt thông qua `/api/redact`. Xóa entity cho phép text đoạn đó xuất hiện lại theo quyết định rà soát; ứng dụng không tự thêm lại đoạn đã xóa. Mọi thay đổi danh sách hoặc lỗi request làm mất xác nhận xuất. Response redact cũ không ghi đè danh sách mới.

### US-04 — Xuất kết quả

AC-07: Chỉ bật tải TXT/JSON khi có preview thành công cho phiên bản input/entities hiện tại và người dùng đã xác nhận rà soát. TXT tải xuống có nội dung trùng preview, mã hóa UTF-8. JSON chỉ gồm `redacted_text` và `metadata`; không có input, chuỗi entity gốc, bản đồ thay thế hoặc tên file gốc.

AC-08: Gán token `[LABEL_n]` theo thứ tự xuất hiện trong mỗi nhãn. Các đoạn có cùng nhãn và cùng chuỗi gốc chính xác dùng cùng token trong một tài liệu. Không gộp theo viết hoa/thường hoặc Unicode normalization. Tài liệu mới bắt đầu đếm từ 1. Nội dung ngoài span được giữ nguyên, gồm ngày tái khám.

### US-05 — Hiểu kết quả thực nghiệm

AC-09: Trang thực nghiệm lấy số liệu từ `/api/evaluation`, không hard-code điểm. Hiển thị ngôn ngữ, số ghi chú, số entity/support từng nhãn, nguồn dữ liệu, train/validation/test theo họ mẫu câu, seed, revision dữ liệu/model/config, exact span + label TP/FP/FN, precision/recall/F1 từng nhãn và micro, số tài liệu còn sót ≥1 định danh, ví dụ lỗi giả lập và lệnh tái tạo. Thiếu artifact hiển thị chưa có kết quả.

AC-10: So sánh rules, NER, hybrid tiếng Việt trên cùng test khóa. NER phải thật sự nạp trọng số/huấn luyện và suy luận; công bố nhãn mô hình hỗ trợ. Đối chứng tiếng Anh dùng cùng input gốc cho Presidio/Philter/GEMINI pyDeid độc lập; khác đơn vị chấm không trình bày như cùng tác vụ. Phân biệt quy trình đánh giá PASS và F1 mục tiêu ≥85% đạt/chưa đạt. Không dùng điểm demo cũ làm điểm bản mới.

### US-06 — Hiểu cách hoạt động và dùng trên nhiều thiết bị

AC-11: Màn hình desktop có văn bản gốc bên trái, bản che bên phải và danh sách chỉnh sửa. 390px xếp dọc, không cuộn ngang trang; nút rà soát/xuất thao tác được. Kiểm tra 1440px/390px, bàn phím Tab/Enter/Space, focus nhìn thấy, nhãn truy cập và tương phản chữ.

AC-12: Mục Cách hoạt động chỉ lazy-load Three.js khi mở; phiếu khám giả lập tách lớp chuyên môn và định danh, bật/tắt lớp che. Tôn trọng reduced motion, giải phóng renderer/geometry/material/listeners khi rời trang. Thiếu WebGL hoặc lỗi tải module có hình tĩnh thay thế và luồng rà soát vẫn hoạt động.

## Tình huống nghiệm thu tối thiểu

1. Câu chưa nằm trong ví dụ: phân tích, đổi nhãn/xóa/thêm, xác nhận, tải TXT rồi mở file đối chiếu preview.
2. Mẫu trong hướng dẫn nhãn: che tên/ngày sinh/mã nhưng giữ `18/12` hẹn tái khám.
3. `🙂 Người bệnh Mai An` và tên tiếng Việt tổ hợp: chọn đoạn đúng, không cắt emoji hoặc mất dấu.
4. Giữ request phân tích đầu chậm, sửa input, chạy request mới; response đầu không tạo lại kết quả cũ.
5. Chỉnh entity sau xác nhận: export bị khóa tới khi preview mới thành công và xác nhận lại.
6. Gửi API span âm, float, bool, vượt cuối, chồng nhau, nhãn lạ: lỗi an toàn không lặp input ra response/log.
7. Hai lần `Mai An` cùng nhãn cho cùng token; tài liệu kế tiếp bắt đầu NAME_1.
8. Tắt WebGL và giả lỗi engine phụ: review/export cơ bản vẫn dùng được, trạng thái không giả thành công.

## Liên kết quy trình

Owner/reviewer/task/evidence được PM quản lý trong `docs/tasks.md` và `docs/progress.md`. Người triển khai chỉ đặt READY_FOR_REVIEW; QA/Dev phải chạy phép kiểm thực tế và ghi kết luận độc lập trong `docs/reviews/Gx.md`. G0 chỉ PASS sau khi skeleton đã chạy và QA có thể viết test từ hợp đồng này.
