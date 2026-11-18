# Kế hoạch triển khai: MedShield

Nhánh `feat/medshield-demo`; ngày 2026-11-18; [đặc tả](spec.md).

## Tóm tắt

Bàn rà soát React gọi FastAPI trong bộ nhớ. Làm quy tắc trước, sau đó NER CRF BIO có trọng số học từ dữ liệu và hybrid xác định. Chấm dự đoán trước sửa tay, CPU Windows.

## Bối cảnh kỹ thuật

Python qua uv, React/TypeScript/Vite qua npm. Router/controller → schema → service → adapter. sklearn-crfsuite học trọng số chuỗi token từ dữ liệu giả lập. Không database bệnh án. Khóa dependency sau smoke; phiên bản thực ở docs/environment.md.

## Kiểm tra constitution

Năm nhãn, codepoint nửa mở, một hợp đồng; source viết tay ≤299 dòng, header/docstring; lint/type/formatter; không log input; model/upstream thực; reviewer độc lập. Chỉ triển khai chặng sau khi chặng trước PASS.

## Cấu trúc dự án

apps/api/: controller, schemas, services, adapters. apps/web/src/: components, hooks, Unicode, trang Three tải lười. ml/: train/features/evaluate/scoring. data/: dữ liệu giả lập chia theo họ. tests/: QA và test cuối. scripts/: setup/check/package. docs/reviews/: review độc lập.

## Pha 0 — Nghiên cứu

Quyết định và nguồn ở [research](../../docs/research.md). Chọn CRF CPU để tái tạo nhanh. Transformer cần thêm tải/huấn luyện và không bắt buộc theo lệnh triển khai. Ba upstream cài riêng, chấm cùng tác vụ tương đương. Research/demo cũ và bảng đối chiếu slide là nguồn thứ cấp, không dùng làm điểm mới.

## Pha 1 — Thiết kế

[data-model.md](data-model.md), [contracts/api.md](contracts/api.md), [quickstart.md](quickstart.md). Hợp đồng chuẩn giữ tại docs/api-contract.md. Task chi tiết tại docs/tasks.md; lịch tại docs/plan.md.

## Thứ tự bàn giao

G0 đặc tả/môi trường → review; G1 web/API/rules/sửa/xuất → review; G2 data/model/adapters → review; G3 đánh giá → review; G4 UX/Three → review; G5 checkout sạch/CI/ZIP/tài liệu/draft PR → review.

## Theo dõi độ phức tạp

Ba upstream không quyết định khả dụng của engine Việt chính nhưng phải thử và công khai. Docker daemon vắng không chặn native Windows; Compose chưa chạy phải ghi đúng. Không bỏ yêu cầu để làm đẹp gate hoặc số điểm.
