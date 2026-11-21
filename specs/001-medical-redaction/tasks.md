# Tasks: MedShield

Thiết kế tại plan.md/spec.md; chi tiết owner/reviewer/AC/evidence trong ../../docs/tasks.md. Task Spec Kit T đánh số trong phạm vi Spec Kit; board docs/tasks.md có ánh xạ riêng. Tests được chủ dự án yêu cầu. Checklist này ghi hoàn thành triển khai, không thay PASS của gate.

## Pha 1 — Setup (G0)

- [x] T001 Kiểm repo/quyền và input trong docs/input-inventory.md (root; Dev review; T001/T002).
- [x] T002 [P] Khởi tạo môi trường và lock trong pyproject.toml, apps/web/package-lock.json (DevOps; Dev/QA; T003/T007).
- [x] T003 [P] Constitution/spec/API/labels trong docs/ và .specify/memory/constitution.md (BA; Dev/QA; T004/T005).
- [x] T004 Board/docs và phân tích consistency trước implement trong docs/tasks.md, docs/reviews/G0.md (PM/root; QA; T006).

## Pha 2 — Nền tảng (G1, sau G0 PASS)

- [x] T005 Xây schemas/error handler trong apps/api/: thực hiện các trường data-model.md AnalyzeRequest.text, AnalyzeRequest.language, AnalyzeRequest.mode, Entity.start, Entity.end, Entity.label, Entity.source, Entity.score, RedactRequest.entities, RedactResponse.redacted_text, RedactResponse.metadata, Engine.name, Engine.status, Engine.mode, Engine.language theo contract (root; QA).

## Pha 3 — User Story 1: Nhập/phân tích (P1)

- [x] T006 [US1] Rules và analyze thật trong apps/api/; nhập UTF8/tô span/version request trong apps/web/src/ (Dev/root; QA; T101/T102).

## Pha 4 — User Story 2: Sửa/xuất (P1)

- [x] T007 [US2] Thêm/xóa/đổi nhãn, redact/preview/duyệt/download trong apps/web/src/ và apps/api/; tests/ kiểm Unicode/race/export (Dev/root; QA+BA; T102/T103).

## Pha 5 — User Story 3: Hiểu AI (P2)

- [ ] T008 [US3] Dữ liệu chia theo họ, train CRF và adapters trong ml/, data/, apps/api/adapters/ (Research; QA/Dev/DevOps; T201–T204).
- [ ] T009 [US3] Scorer/evaluate/artifact và trang kết quả trong ml/, artifacts/, apps/web/src/ (Research/Dev; QA/BA; T301–T303).
- [ ] T010 [US4] UX 390/1440px và Three.js lazy/fallback/cleanup trong apps/web/src/; tests/ (Dev; QA/BA/DevOps; T401–T403).

## Pha 6 — Hoàn thiện (G5)

- [ ] T011 CI/setup/Compose/docs/ZIP/draft PR trong scripts/, .github/, README.md, docs/; clean checkout và ZIP verification (DevOps/PM/root; QA+agent ngoài DevOps; T501–T505).

## Phụ thuộc và chiến lược

T001–004 hoàn thành và G0 review PASS trước T005–007. G1 PASS trước T008; G2 PASS trước T009; G3 PASS trước T010; G4 PASS trước T011. [P] chỉ khác file trong cùng gate. Ví dụ G0 BA viết docs cùng DevOps viết môi trường. MVP đầu là US1/US2, tiếp tục đủ các chặng theo lệnh người dùng. Nguồn thực nghiệm và constraints chỉ tham chiếu canonical contract, không chép lại số khác.


