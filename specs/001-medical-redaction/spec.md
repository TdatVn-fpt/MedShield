# Feature Specification: MedShield — nhận diện và che định danh y tế

**Feature Branch**: `feat/medshield-demo`

**Created**: 2026-11-18

**Status**: READY_FOR_REVIEW

**Input**: Yêu cầu triển khai toàn dự án của Nguyễn Tiến Đạt, SIC AI-NIC4. Phạm vi chi tiết và AC ổn định được giữ tại [docs/spec.md](../../docs/spec.md); đây là entry point Spec Kit theo template release đã khởi tạo, không thay đổi các AC đó.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Nhập và phân tích ghi chú (Priority: P1)

Người dùng dán/TXT UTF-8 hoặc nạp ví dụ giả lập, phân tích và xem các đoạn định danh có nhãn/nguồn. Ánh xạ US-01/US-02, AC-01–04 trong đặc tả chi tiết.

**Why this priority**: Đây là đầu vào của mọi quyết định rà soát.

**Independent Test**: Nhập câu ngoài demo; phân tích qua request API thật, kiểm tra highlight và ngày tái khám.

**Acceptance Scenarios**:

1. **Given** ghi chú hợp lệ, **When** phân tích, **Then** entities không chồng lấn, offset code point đúng substring, engine đúng thực tế.
2. **Given** request chưa trả, **When** sửa input, **Then** entities/preview/xác nhận cũ bị hủy và response cũ không ghi đè.

### User Story 2 - Sửa và xuất sau rà soát (Priority: P1)

Người dùng thêm/xóa/đổi nhãn, xem preview và xác nhận để tải TXT/JSON. Ánh xạ US-03/US-04, AC-05–08.

**Why this priority**: Đầu ra phải phản ánh quyết định người rà soát, kể cả khi máy nhận diện sai.

**Independent Test**: Thực hiện sửa trên một ghi chú, tải TXT và mở để đối chiếu preview; JSON không chứa input/entity gốc.

**Acceptance Scenarios**:

1. **Given** entities tự động, **When** xóa hoặc đổi nhãn/thêm đoạn, **Then** preview tương ứng danh sách mới và xác nhận cũ mất hiệu lực.
2. **Given** preview hiện hành đã rà soát, **When** xác nhận và tải, **Then** TXT trùng preview, token tên lặp nhất quán trong tài liệu.

### User Story 3 - Đọc bằng chứng AI (Priority: P2)

Người dùng đọc số mẫu, phương pháp, điểm từng nhãn và lỗi có thể giải thích. Ánh xạ US-05, AC-09–10.

**Why this priority**: Chủ dự án phải bảo vệ đóng góp AI bằng kết quả tái tạo được.

**Independent Test**: Chạy script đánh giá trên test khóa rồi đối chiếu artifact với dashboard.

**Acceptance Scenarios**:

1. **Given** chưa có artifact, **When** mở trang, **Then** hiển thị chưa có kết quả, không hiện điểm giả.
2. **Given** artifact thực nghiệm, **When** đọc dashboard, **Then** số mẫu/support/TP/FP/FN/F1 và trạng thái từng engine khớp artifact, ngôn ngữ và đơn vị chấm rõ.

### User Story 4 - Sử dụng linh hoạt và hiểu minh họa (Priority: P2)

Người dùng thao tác bằng bàn phím trên desktop/mobile và mở mô hình tách lớp định danh. Ánh xạ US-06, AC-11–12.

**Why this priority**: Buổi demo cần luồng rõ ràng kể cả khi phần 3D không khả dụng.

**Independent Test**: Kiểm 390px/1440px, bàn phím và WebGL tắt.

**Acceptance Scenarios**:

1. **Given** mobile 390px, **When** rà soát/xuất, **Then** thao tác không yêu cầu cuộn ngang trang.
2. **Given** WebGL hoặc module lỗi, **When** mở Cách hoạt động, **Then** có hình tĩnh thay thế, rà soát vẫn hoạt động.

### Edge Cases

- UTF-8 BOM bỏ trước tạo input; CRLF, emoji và dấu tổ hợp được giữ đúng sau đó.
- Text trống/quá 50.000 code point, >2.000 spans, nhãn lạ, số thực/bool cho offset, span âm/ngoài/chồng nhau bị từ chối bằng lỗi an toàn.
- Entity rỗng sau rà soát là hợp lệ; input mới hoặc sửa entities làm mất quyền xuất tới khi preview/xác nhận mới hoàn tất.
- Tên lặp chỉ dùng cùng token nếu cùng nhãn và chuỗi gốc chính xác; không gộp Unicode/case tự động.
- Engine thiếu model/ngôn ngữ không sẵn sàng hiển thị 503, không fallback âm thầm.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: MUST nhập/dán/TXT UTF-8/ví dụ giả lập và xử lý trạng thái đầu vào theo AC-01–02.
- **FR-002**: MUST gọi phân tích thật, hiển thị nhãn/nguồn/vị trí và engine đúng thực tế theo AC-03–04.
- **FR-003**: MUST thêm/xóa/đổi nhãn, kiểm tra spans, preview và rà soát theo AC-05–06.
- **FR-004**: MUST khóa xuất trước xác nhận, xuất TXT/JSON tối thiểu và token lặp nhất quán theo AC-07–08.
- **FR-005**: MUST công bố artifact đánh giá thật, provenance/split/revision và phân biệt mục tiêu F1 với quy trình đánh giá theo AC-09–10.
- **FR-006**: MUST sử dụng được 390px/1440px, bàn phím và fallback Three.js theo AC-11–12.
- **FR-007**: MUST bảo vệ input/log/lỗi trong bộ nhớ theo constitution và hợp đồng API.
- **FR-008**: MUST có review độc lập G0–G5, lock dependencies, CI và hướng dẫn Windows/bộ ZIP đã kiểm tra.

### Key Entities *(include if feature involves data)*

- **Document**: chuỗi nguyên bản trong bộ nhớ và phiên bản input phục vụ chặn response cũ; không lưu lâu dài.
- **Entity**: `start,end,label,source,score`, năm nhãn theo annotation guide; code point half-open.
- **Review**: danh sách entities hiện hành, preview phiên bản tương ứng và trạng thái xác nhận.
- **Evaluation**: artifact script với dataset/model revision, split, provenance, điểm/support và trạng thái engine; không phải kết quả sửa tay.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Một ghi chú chưa có trong demo đi xuyên suốt phân tích → sửa → xác nhận → tải; file TXT trùng preview và giữ ngày tái khám trong ca chuẩn.
- **SC-002**: Các ca Unicode/CRLF/BOM/tên lặp và response cũ đều có kiểm chứng đúng; lỗi không lặp input vào log/response.
- **SC-003**: Rules/NER/hybrid tiếng Việt thực sự chạy trên cùng test khóa; số liệu chấm chính xác tái tạo được. F1 mục tiêu ≥85% từng nhãn chính được báo đạt/chưa đạt, không phải điều kiện để làm giả hoặc sửa test.
- **SC-004**: Presidio/Philter/GEMINI pyDeid mỗi công cụ được thử smoke; không chạy được phải có trạng thái và lệnh tái hiện, không công bố thành công cả ba khi thiếu bằng chứng.
- **SC-005**: Luồng sửa/xuất dùng được ở 390px và 1440px, bàn phím, khi WebGL tắt; export JSON không chứa trường input/entity gốc.
- **SC-006**: Checkout sạch và ZIP giải nén chạy theo README; repo/branch/commit/PR/CI được báo theo trạng thái thật.

## Assumptions

- Dùng ghi chú giả lập được phép chia sẻ; không có yêu cầu xử lý hồ sơ bệnh nhân thật hoặc chứng nhận pháp lý.
- Chạy cục bộ một người dùng, CPU, không đăng nhập/database; tải dependency/model ban đầu cần mạng.
- Khoảng 100 ghi chú là mục tiêu khả thi, báo số thực; người học chưa tự rà soát thì số human review bằng 0.
- Lựa chọn thuận nghịch đã được chủ dự án giao Tech Lead; không hỏi duyệt từng gate. Điểm mơ hồ nhãn/offset/token đã chốt trong contract và annotation guide; không còn mục NEEDS CLARIFICATION trước review G0.

