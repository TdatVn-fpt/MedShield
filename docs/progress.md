# Tiến độ MedShield

Chủ dự án: Nguyễn Tiến Đạt — Samsung Innovation Campus, AI-NIC4. Cập nhật khởi tạo: 18/11/2026 (Asia/Saigon).

Đây là sổ điều phối; trạng thái mô tả bằng chứng đã có, không phải lời hứa. PM chỉ ghi READY_FOR_REVIEW cho sản phẩm mình soạn. Reviewer độc lập mới kết luận PASS sau khi đọc sản phẩm và tự chạy phép kiểm liên quan.

## Bảng chặng

| Chặng | Phạm vi bắt buộc | Người làm | Người kiểm tra | Đầu ra/bằng chứng đích | Trạng thái | Phụ thuộc |
|---|---|---|---|---|---|---|
| G0 | Kiểm tra checkout/remote; Spec Kit/constitution; spec, API mẫu, annotation guide; board; môi trường và skeleton chạy | PM, BA, DevOps; Tech Lead tích hợp | Dev: khả thi/skeleton; QA: khả năng viết test | Các tài liệu đặc tả, lock/môi trường và `docs/reviews/G0.md` | PASS | Quyền đọc repo và công cụ cục bộ |
| G1 | Nhập/TXT UTF-8 → API thật → baseline → rà soát thêm/xóa/đổi nhãn → duyệt → xuất TXT/JSON; vô hiệu kết quả cũ | Dev; Research cung cấp ví dụ | QA chạy câu mới và mở TXT; BA đối chiếu quyết định | Source web/API, test/browser và `docs/reviews/G1.md` | PASS | G0 PASS |
| G2 | Dataset chia theo họ câu; NER tiếng Việt, rules và hybrid chạy thật; thử ba adapter upstream; Unicode; cài lại engine chính | Research/ML; Dev tích hợp | QA: split/Unicode/smoke; Dev: contract; DevOps: tái cài | Dataset/model/script/adapter, smoke và `docs/reviews/G2.md` | PASS | G1 PASS |
| G3 | Exact span + label, TP/FP/FN/support, micro-F1, số ghi chú còn sót; khóa test và artifact tái tạo; lỗi thực | Research/ML | QA tính tay và chạy lại; BA kiểm ý nghĩa; Dev đối chiếu dashboard | Artifact, báo cáo và `docs/reviews/G3.md` | PASS | G2 PASS với phạm vi adapter được công khai |
| G4 | UX 390/1440px, bàn phím/focus, luồng rà soát đầy đủ; nhập PDF có lớp chữ; Three.js tải lười, cleanup/reduced motion/WebGL fallback; build sạch | Dev | QA: UI; BA: nghiệp vụ; DevOps: build/fallback | Test UI, [kế hoạch nhập PDF](plan-nhap-pdf-benh-an.md) và `docs/reviews/G4.md` | IN_PROGRESS | G3 PASS |
| G5 | Windows/checkout sạch, CI, README, Mermaid, báo cáo/đóng góp, slide Markdown 6 trang, demo 3 phút, defense Q&A; ZIP đã giải nén; draft PR nếu có quyền | DevOps, PM; Tech Lead tích hợp | QA + agent ngoài DevOps chạy sạch; PM đối chiếu yêu cầu | Build, Git/PR/CI thật, ZIP và `docs/reviews/G5.md` | TODO | G4 PASS |

## Quyền sở hữu và review

| Vai trò | File/phạm vi sở hữu mặc định | Review chính |
|---|---|---|
| PM | `docs/progress.md`, `docs/tasks.md`, `docs/plan.md`; tài liệu demo/bàn giao được giao sau | QA/Dev kiểm G0; Tech Lead đối chiếu bàn giao |
| BA | Spec/user stories, annotation guide, API contract | Dev kiểm triển khai; QA kiểm test được |
| Research/ML | `ml/`, `data/`, adapter được giao; báo cáo thực nghiệm | QA/Dev/DevOps theo G2–G3 |
| Dev | `apps/web/`, `apps/api/`, trừ adapter giao Research | QA + BA |
| QA | `tests/`, fixtures test cuối, `docs/reviews/` | Dev/BA review test; Tech Lead phân xử |
| DevOps | `.github/`, `scripts/`, lock/build/vận hành | QA + Dev hoặc Research |

Một file chỉ có một người sửa tại một thời điểm. Tech Lead thông báo chuyển quyền sở hữu khi cần. Runtime có ba slot subagent đồng thời: gọi sáu vai trò theo lượt, không ghi nhận vai trò chưa thực sự chạy là reviewer.

## Quy tắc trạng thái

`TODO → IN_PROGRESS → READY_FOR_REVIEW → PASS`. Khi có lỗi: `CHANGES_REQUESTED → IN_PROGRESS → READY_FOR_REVIEW`. BLOCKED phải ghi trở ngại, lệnh tái hiện và ảnh hưởng. Chưa PASS chặng hiện tại thì chỉ điều tra hoặc chuẩn bị tài liệu cho chặng sau.

Mỗi `docs/reviews/Gx.md` do reviewer lập phải ghi tác giả, reviewer thực tế, SHA hoặc phiên bản file, từng tiêu chí, lệnh/thao tác, kỳ vọng/quan sát, lỗi còn mở và kết luận. Không dùng board này thay biên bản review. Thay đổi sau PASS phải mở lại phạm vi review liên quan.

## Nhật ký

| Ngày | Sự kiện | Trạng thái/bằng chứng |
|---|---|---|
| 18/11/2026 | PM đọc đầy đủ lệnh triển khai và tạo board/kế hoạch/task G0 | Bộ tài liệu PM READY_FOR_REVIEW; toàn G0 vẫn IN_PROGRESS, chưa có kết luận reviewer |
| 18/11/2026 | Tech Lead thông báo remote trống có quyền ghi; baseline `main` `6e227b0` đã push, nhánh làm việc `feat/medshield-demo`; tìm thấy research ZIP ngoài repo | Đây là thông tin bàn giao từ Tech Lead, PM chưa tự xác minh Git; `C:\Users\Admin\Downloads\MedShield_SIC_Research.zip` không được copy nguyên lên repo |
| 21/11/2026 | Tiếp nhận thay đổi G1 từ Claude tại `8984577`, xác minh lại origin và quyền GitHub, phân công sáu vai trò kiểm tra. | Biên bản BA và file xuất giả lập có sẵn. Dev tái hiện lỗi đọc TXT đến muộn và lỗi hợp đồng API. G1 mở vòng sửa và tái kiểm. |
| 22/11/2026 | Hoàn thiện PDF-01–PDF-04 và nghiệm thu độc lập phạm vi PDF. | 9/9 test PDF qua. Biên bản `docs/reviews/G4-pdf.md` và hướng dẫn `docs/huong-dan-nhap-pdf.md`. |
| 23/11/2026 | Kiểm lại bản triển khai trên Windows và giữ nguyên byte PDF khi checkout bằng Git. | PDF-01–PDF-04 PASS. Có 22/22 test Chromium và 55/55 test backend qua khi kiểm lại. G4 tổng thể vẫn IN_PROGRESS. |

## Các điểm phải công khai khi bàn giao

- Tách quy trình đánh giá PASS với mục tiêu F1 ≥85% đạt/chưa đạt; không sửa test để nâng điểm.
- Mỗi adapter: đã chạy có bằng chứng / đã tích hợp chưa chạy được / chưa tích hợp. Job skip không là smoke PASS.
- Dữ liệu agent sinh/kiểm và số mẫu chủ dự án trực tiếp rà soát phải được ghi riêng; chưa có xác nhận thì không ghi chủ dự án đã rà soát.
- Chỉ công bố URL, SHA, PR, CI, ZIP và số liệu đã kiểm chứng; phần chưa xác minh trên Windows/GitHub phải ghi rõ.

G0 | PASS | PM/BA/DevOps/root | QA + Dev | docs/reviews/G0.md, G0-dev.md | Mở G1 (web/API thực).


G1 | PASS | Dev và Tech Lead | QA và BA | docs/reviews/G1.md, docs/reviews/G1-ba.md | Mở G2.
