# Quy ước làm việc MedShield

Đọc `.specify/memory/constitution.md`, `docs/spec.md`, `docs/api-contract.md`, `docs/annotation-guide.md` trước sửa. Chỉ thao tác trong checkout MedShield đã xác minh; không đổi origin repo khác. Repo đích `https://github.com/TdatVn-fpt/MedShield.git`.

## Phân công và gate

Sáu vai trò PM, BA, Research/ML, Dev, QA, DevOps theo yêu cầu chủ dự án; thiếu slot thì xếp lượt/tái sử dụng agent. Không giả danh kiểm tra độc lập. Owner/reviewer/task IDs nằm trong `docs/tasks.md`; trạng thái hiện hành trong `docs/progress.md`. Một file chỉ một người viết tại một thời điểm. Tác giả chỉ READY_FOR_REVIEW, reviewer chạy kiểm tra và ghi `docs/reviews/Gx.md` mới PASS. Chưa PASS chặng hiện tại chỉ chuẩn bị/điều tra chặng sau. Sửa phần đã PASS phải review lại.

## Hợp đồng và source

- UI/tài liệu tiếng Việt; biến/hàm/module/API tiếng Anh.
- Source viết tay Python/JS/TS/JSX/TSX/CSS và test ≤299 dòng vật lý, kể cả blank/comment; loại generated/dependency/lock/data/Markdown. Không nén logic để lách.
- Comment đầu source ghi đường dẫn tương đối và mục đích; sau shebang/directive bắt buộc nếu có. Hàm nghiệp vụ, handler, public/export, hook có docstring/JSDoc mô tả tên, input/output, hành vi đáng chú ý.
- Backend tách router/controller, schema, service, adapter. Frontend component và hook state. Typecheck/lint/formatter; dependency khóa sau smoke thành công.
- Unicode code point `[start,end)` là chuẩn API. Browser đổi UTF-16 selection đúng; không normalize text sau tính offsets. Entity không chồng lấn. Xem contract cho giới hạn/lỗi.
- Input/entities đổi làm mất preview/xác nhận; chặn response cũ; export chỉ bản che và metadata sau rà soát.
- Không log/persist input, token map, secret. Error handler không trả Pydantic input/exception stack. Chỉ artifact giả lập được phép chia sẻ.
- Nguồn/revision/license của code/model tái dùng ghi `THIRD_PARTY.md`. Engine không chạy phải có trạng thái/lý do/lệnh tái hiện, không giả output.

## Lệnh và kiểm tra

Lệnh setup/start/test chính thức do DevOps ghi README và script sau smoke; không đoán kết quả từ tài liệu. Trước thay đổi, chạy `git status --short --branch` và đọc file liên quan. Trước review, chạy đúng lệnh lint/typecheck/test/build/299 dòng của phạm vi đã triển khai và ghi output thực tế. Browser phải kiểm tra request thật, sửa → xuất, input mới vô hiệu kết quả cũ, 390px/1440px, Unicode và WebGL fallback. Không ghi PASS khi chưa chạy kiểm tra.

Spec Kit do Tech Lead khởi tạo theo release thực tế và `specify init --help`; tái dùng cấu hình sẵn, không dùng force ghi đè khi chưa đọc diff. Các tài liệu BA trong G0 thể hiện constitution/specify/clarify, PM quản lý plan/tasks; analyze phải kiểm tra consistency trước implement. Git feature branch, commit nhỏ, không force-push hoặc tự merge main. Không đưa slide khóa học nguyên bộ vào repo.
