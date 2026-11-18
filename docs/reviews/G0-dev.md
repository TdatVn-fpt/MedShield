# G0 — Review khả năng triển khai của Dev

Ngày 18/11/2026, Windows PowerShell. Reviewer thực tế: subagent Dev. Tác giả: BA (spec/contract/labels/constitution), PM (board/plan), DevOps (skeleton/locks), Tech Lead (Spec Kit). Phiên bản review: working tree trên `feat/medshield-demo`, baseline `6e227b0`; các file G0 đang untracked, chưa có commit tích hợp.

## Tiêu chí và kiểm tra thực tế

| Tiêu chí | Lệnh/kiểm tra reviewer tự chạy | Quan sát |
|---|---|---|
| Giao diện skeleton build được | Trong `apps/web`: `npm run build` | PASS: TypeScript + Vite 8.3.8, 16 modules, JS 219,69 kB |
| Lint và định dạng web | `npm run lint`; `npm run format:check` | PASS: không lỗi; tất cả source theo Prettier |
| API skeleton chạy được | `.venv/Scripts/python.exe -X utf8 -c "from fastapi.testclient import TestClient; from apps.api.main import app; r=TestClient(app).get('/health'); print(r.status_code,r.json()); assert r.status_code==200; assert r.json()['status']=='ok'"` | PASS: HTTP200, status ok; engine rules công khai unavailable, chưa giả có phân tích |
| Source đúng giới hạn/header | `python -X utf8 scripts/check_source.py` | PASS: `Source policy: 0 violation(s)` |
| Ví dụ offsets implementable | Python slice `[11:17]`, `[29:39]`, `[44:52]` trên câu API | PASS: lần lượt Mai An, 03/02/1995, BN-00071 |
| Contract đủ triển khai | Đọc Entity/request/response/errors và AC-01–12 | Có strict integer/half-open codepoint, score/labels, overlap, giới hạn, no-input errors, stale response, approval/export; không có mơ hồ chặn code |
| Nhãn nhất quán | Đọc annotation guide và API contract | Phân biệt DOB/ngày hẹn, địa chỉ gồm TP., repeated exact slice; có thể viết test cụ thể |

## Lưu ý và phạm vi

- Python venv hoạt động là 3.11.7; DevOps đang cập nhật environment/lock sau phương án tải 3.12 chậm. Không suy từ phiên bản dự kiến rằng 3.12 đã chạy.
- TestClient phát cảnh báo deprecation của Starlette/httpx nhưng phép kiểm thành công. Chưa phải lỗi khởi động.
- PM board dùng US-01–08 khác cách chia US-01–06 của BA spec. Khi triển khai dùng AC-01–12 và đường dẫn tài liệu làm chuẩn; Tech Lead nên bổ sung mapping IDs ở board để tránh dẫn sai story. Không thay đổi nội dung acceptance.
- Docker daemon chưa chạy; G0 native Windows vẫn chạy. Chưa kiểm Docker Compose.
- Đây là review Dev về skeleton và khả năng triển khai. Chưa chứng minh request trình duyệt, phân tích/NER, xuất file hoặc UI hoàn chỉnh. QA kết luận G0 tích hợp sau khi kiểm tài liệu Spec Kit plan/tasks/analyze và môi trường cuối.

## Kết luận

**PASS cho phạm vi Dev G0**: web/API skeleton chạy được và contract triển khai được. Không tự chuyển trạng thái gate tổng hoặc triển khai G1 trước thông báo G0 PASS tích hợp của Tech Lead/QA. Thay source skeleton hoặc contract sau review cần mở lại phạm vi liên quan.
