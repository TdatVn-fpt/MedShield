# Task board và truy vết nghiệm thu

Khởi tạo 18/11/2026. Trạng thái trong bảng là của task, không tự suy ra PASS cho gate. Bằng chứng ghi là đích cần tạo nếu chưa tồn tại. PM không tự duyệt sản phẩm của mình.

## User stories

| ID | Người dùng cần | Chặng |
|---|---|---|
| PM-US-01 | Chạy ứng dụng cục bộ từ hướng dẫn Windows với môi trường tái tạo | G0, G5 |
| PM-US-02 | Dán/TXT UTF-8 hoặc dùng ví dụ giả lập rồi phân tích bằng API thật | G1 |
| PM-US-03 | Định vị và sửa nhãn, xóa che nhầm, thêm đoạn bỏ sót; sửa input làm mất kết quả/duyệt cũ | G1, G4 |
| PM-US-04 | Xem trước, xác nhận rà soát, tải TXT/JSON an toàn; tên lặp dùng cùng ký hiệu trong tài liệu | G1, G4 |
| PM-US-05 | Biết rules/NER/hybrid và từng upstream nào thực sự đã chạy | G2 |
| PM-US-06 | Giải thích AI bằng số mẫu, support, TP/FP/FN/F1 và lỗi tái tạo từ artifact | G3 |
| PM-US-07 | Dùng được mobile/desktop/bàn phím, xem minh họa 3D có fallback | G4 |
| PM-US-08 | Demo, bảo vệ và nộp source có bằng chứng review/CI/ZIP | G5 |

## Tasks G0

| ID | Story | Việc và tiêu chí chấp nhận | Owner | Reviewer | Bằng chứng đích | Trạng thái |
|---|---|---|---|---|---|---|
| T001 | PM-US-01 | Xác minh root, Git/status/nhánh/lịch sử/origin/remote và quyền; bảo toàn dữ liệu hiện hữu | Tech Lead | DevOps | Ghi lệnh và quan sát môi trường trong tài liệu G0 | TODO |
| T002 | PM-US-01 | Tìm research HTML, đề/slide NLP/evaluation và demo cũ; ghi file có/thiếu, không đưa slide lên Git | Research/ML | BA | Bảng nguồn research | TODO |
| T003 | PM-US-01 | Kiểm phiên bản Python/Node/Git/Docker/browser, khả năng tải model; dependency smoke rồi lock | DevOps | Dev | Báo cáo môi trường, lockfile và lệnh smoke | TODO |
| T004 | PM-US-01 | Spec Kit đúng release: help/init phù hợp checkout; constitution và quy ước agent, không overwrite mù | DevOps + Tech Lead | Dev | `.specify/memory/constitution.md`, `AGENTS.md`, log CLI | TODO |
| T005 | PM-US-02–04 | Spec, annotation guide 5 nhãn, giới hạn/offset/entity/error chung, API có ví dụ request/response | BA | QA + Dev | Spec/API/guide và review G0 | TODO |
| T006 | PM-US-08 | Board G0–G5, owner/reviewer/phụ thuộc, plan và task truy vết đầy đủ | PM | QA + Dev | `docs/progress.md`, `docs/plan.md`, `docs/tasks.md` | READY_FOR_REVIEW |
| T007 | PM-US-01 | Skeleton web/API khởi động; Dev tự chạy, QA viết được test từ spec | DevOps/Dev | QA | Lệnh thực và `docs/reviews/G0.md` | TODO |
| T008 | PM-US-07 | Tìm skill UI/UX/Three.js có thật; nếu thiếu, đọc tài liệu chính thức và ghi hướng dẫn Dev | Research/ML | Dev | Bảng nguồn và quyết định UI/3D | TODO |

## Tasks sau G0 (chưa triển khai chính thức)

| ID | Gate / story | Việc và tiêu chí chấp nhận | Owner | Reviewer | Bằng chứng đích | Trạng thái |
|---|---|---|---|---|---|---|
| T101 | G1 / PM-US-02 | Nhập/TXT BOM/example → analyze thật; tô span/nhãn/nguồn và trạng thái empty/loading/success/error/unavailable | Dev | QA | Test API + browser, `docs/reviews/G1.md` | PASS |
| T102 | G1 / PM-US-03 | Bấm mục định vị, đổi nhãn/xóa/thêm; sửa input hủy kết quả/duyệt; response cũ không ghi đè | Dev | QA + BA | Ca câu mới, ca race và thao tác UI | PASS |
| T103 | G1 / PM-US-04 | Redact validate nhãn/biên/chồng lấn; preview/duyệt/TXT/JSON; tên lặp nhất quán; giữ ngày tái khám | Dev | QA + BA | TXT đã tải và mở, JSON không chuỗi gốc | PASS |
| T201 | G2 / PM-US-05 | Khoảng 100 ghi chú nếu khả thi; split theo họ trước sinh; tự do/âm tính/lowercase/địa chỉ/date/numeric; ghi tác giả và human review thật | Research/ML | QA | `data/`, manifest seed/revision/split | PASS |
| T202 | G2 / PM-US-05 | NER CPU thực, rules và hybrid; giữ nguồn, trọng số/revision/license, script train/load và phạm vi nhãn | Research/ML | Dev + QA | `ml/`, model metadata, smoke tiếng Việt | PASS |
| T203 | G2 / PM-US-05 | Xác minh/cài riêng/thử Presidio, Philter UCSF, GEMINI pyDeid đúng nguồn; status và lỗi tái hiện nếu blocked | Research/ML | QA + DevOps | Ba lệnh smoke/output thật; `THIRD_PARTY.md` | PASS |
| T204 | G2 / PM-US-03 | Emoji, tổ hợp dấu, CRLF, BOM, lặp tên; contract code point/UTF-16 đúng; cài lại engine chính | QA + DevOps | Dev | Tests độc lập, `docs/reviews/G2.md` | PASS |
| T301 | G3 / PM-US-06 | Rules/NER/hybrid chung test khóa; exact span+label, per-label support/TP/FP/FN/P/R/F1, micro và ghi chú còn sót | Research/ML | QA | Artifact và lệnh evaluate tái tạo | PASS |
| T302 | G3 / PM-US-06 | QA tính tay scorer rồi chạy lại; BA kiểm nhãn; dashboard khớp artifact, lỗi thật và mục tiêu F1 riêng | QA; Dev hiển thị | BA + Tech Lead | `docs/reviews/G3.md`, artifact, báo cáo | PASS |
| T303 | G3 / PM-US-05–06 | Đối chứng upstream độc lập trên cùng Anh ngữ giả lập; đơn vị/nhiệm vụ tương đương hoặc ghi rõ không so sánh | Research/ML | QA | Artifact tiếng Anh, phạm vi adapter và lý do thiếu | PASS |
| T401 | G4 / PM-US-07 | Layout sáng xanh bệnh viện 390/1440px, keyboard/focus/contrast, nhãn chữ+màu, nút review/export dễ dùng | Dev | QA + BA | Browser desktop/mobile và `docs/reviews/G4.md` | TODO |
| T402 | G4 / PM-US-07 | Three.js tải lười phiếu giả lập hai lớp; bật/tắt che, reduced motion, cleanup, WebGL/static fallback; review vẫn chạy khi 3D lỗi | Dev | QA + DevOps | Browser test 3D/fallback/build | TODO |
| T403 | G4 / PM-US-03–04 | Nghiệm thu thêm/xóa/đổi nhãn/duyệt/xuất; payload xuất không lẫn dữ liệu bị che và lỗi upstream phụ an toàn | Dev | BA + QA | Ca đầy đủ và log không nội dung đầu vào | TODO |
| PDF-01 | G4 / PM-US-02 | Tạo PDF ngoại trú giả lập có lớp chữ và đối chiếu với bản chữ kỳ vọng | BA | QA | PDF mẫu và hướng dẫn demo | PASS |
| PDF-02 | G4 / PM-US-02 | Trích chữ PDF trong trình duyệt, chọn trang, kiểm lỗi và giới hạn | Dev | QA | Lock PDF.js, build và các ca dữ liệu thử | PASS |
| PDF-03 | G4 / PM-US-02–04 | Áp dụng bản chữ vào luồng hiện tại, vô hiệu kết quả cũ, giữ hồi quy TXT | Dev | QA | Browser PDF → sửa → xác nhận → TXT/JSON | PASS |
| PDF-04 | G4 / PM-US-07–08 | Kiểm Windows, hai viewport, bàn phím, đo thời gian và viết hướng dẫn | Dev + PM | QA | [Biên bản PDF](reviews/G4-pdf.md) và [kịch bản 3 phút](huong-dan-nhap-pdf.md) | PASS |
| T501 | G5 / PM-US-01 | Setup PowerShell, env example, Docker Compose, locks, ignore, PR template, source max299 + lint/type/test/build/browser CI | DevOps | QA + Dev | `.github/`, `scripts/`, cấu hình và log CI thật | TODO |
| T502 | G5 / PM-US-08 | README/ba lỗi khởi động/Mermaid khớp code/báo cáo/đóng góp/6 slide/demo3p/defense Q&A đúng artifact | PM + DevOps + Research/BA theo file | QA + Tech Lead | Tài liệu bàn giao và đối chiếu yêu cầu | TODO |
| T503 | G5 / PM-US-01–08 | QA + agent ngoài DevOps theo README từ checkout sạch: web, input/export, evaluate; ghi môi trường Windows thật | QA + Dev | Tech Lead | `docs/reviews/G5.md` và lệnh/quan sát | TODO |
| T504 | G5 / PM-US-08 | ZIP chỉ source/config/data giả lập/docs; loại git/env/secret/node_modules/model không được phân phối; giải nén kiểm README | DevOps | QA | ZIP thực, manifest và lần kiểm giải nén | TODO |
| T505 | G5 / PM-US-08 | Feature branch/commit nhỏ; kiểm remote rồi push/draft PR nếu có quyền; không force/merge main; đọc và xử lý CI | DevOps/Tech Lead | QA + PM | SHA/PR/CI thật hoặc lệnh push local đúng | TODO |

## Chính sách bằng chứng

Mỗi reviewer tự chạy ít nhất một kiểm tra liên quan và ghi kỳ vọng/quan sát thực, phiên bản được review, lỗi/retest vào `docs/reviews/Gx.md`. Chưa tồn tại bằng chứng thì không đánh PASS. Sau thay đổi liên quan, mở lại review. Không dùng output mô phỏng làm upstream/model chạy thật; không sửa đáp án/test để nâng F1; kết quả test chỉ đo trước sửa tay.

## Ánh xạ sang user story BA chuẩn

PM-US là nhóm công việc điều phối, không phải ID story BA. ID chuẩn nghiệm thu giữ trong docs/spec.md.

| Nhóm PM | Story BA chuẩn |
|---|---|
| PM-US-01 vận hành | OPS (yêu cầu vận hành xuyên suốt) |
| PM-US-02 nhập/phân tích | US-01, US-02 |
| PM-US-03 rà soát | US-03; vô hiệu đầu vào ở US-01 |
| PM-US-04 xuất | US-04 |
| PM-US-05 engines | US-02, US-05 |
| PM-US-06 thực nghiệm | US-05 |
| PM-US-07 UX/3D | US-06 |
| PM-US-08 bàn giao | OPS và US-05 |

## Đợt nâng chất lượng tiếng Việt

| ID | Phạm vi | Người làm | Người kiểm tra | Trạng thái |
|---|---|---|---|---|
| Q1 | Rules tiếng Việt, validator và ca âm/dương từng nhãn | Dev, QA | Reviewer Phase Q | CHANGES_REQUESTED: DOB/PHONE trên tập gốc |
| Q2 | Đề xuất tên lặp chính xác trong ghi chú | Dev, QA | Reviewer Phase Q | READY_FOR_REVIEW |
| Q3 | Khóa hash, bộ test riêng và runner so sánh cùng scorer | Research/ML, BA | Reviewer Phase Q | READY_FOR_REVIEW |
| Q4 | Hợp nhất theo nhãn, quét ngưỡng validation và công bố ablation | Dev, Research/ML | Reviewer Phase Q | CHANGES_REQUESTED: giảm ADDR |
| M1–M4 | Gán đôi, dữ liệu và mô hình mới | BA, Research/ML, Dev | QA | TODO, chờ nghiệm thu Q |
| L1–L4 | OCR, che PDF, surrogate/batch và vận hành | Dev, DevOps | QA, BA | TODO, chờ nghiệm thu M |

[Báo cáo Phase Q](phase-q.md) ghi bước đã thực hiện, kết quả và lý do dừng. Phạm vi G4/G5 tiếp tục theo bảng chặng hiện hành.

| ID | Phạm vi | Người làm | Người kiểm tra | Trạng thái |
|---|---|---|---|---|
| Q2.1–Q2.5 | PHONE hai tầng, DOB/ID theo ngữ cảnh, hợp nhất và biên, harness hồi quy | Dev, Research/ML, QA | Reviewer Q2 | PASS cổng hồi quy theo [biên bản độc lập](reviews/phase-q2.md) |
| E1–E3 | Nguồn độc lập, gán đôi, phân xử, IAA, SHA-256 và đăng ký cổng M | Chủ dự án, Research/ML, DevOps | QA | IN_PROGRESS. QA đã xác nhận ánh xạ train v3, hai lượt A khớp mốc bàn giao. Đang chạy tiếp B. IAA, phân xử và khóa chờ kết quả B. |
| M1–M4, L1–L6 | Học mô hình và hoàn thiện sản phẩm theo mục tiêu đang hoạt động | Các vai trò theo Phase M và L | QA và chủ dự án | Đã chuẩn bị môi trường và dữ liệu M.1 phía train. Fine-tune thử chờ gói phân xử. Chọn mô hình chờ khóa Phase E. |
