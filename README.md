# MedShield

MedShield nhận diện và che thông tin định danh trong ghi chú y tế. Bạn có thể dán văn bản, tải TXT UTF-8 hoặc nhập PDF có lớp chữ, rồi rà soát trước khi xuất TXT hoặc JSON. Dự án của Nguyễn Tiến Đạt, Samsung Innovation Campus, AI-NIC4.

## Mở folder nào để đọc?

| Thư mục | Nhiệm vụ | Mở trước |
|---|---|---|
| [`apps/`](apps/) | Hai thành phần chạy khi mở MedShield. `web/` phục vụ giao diện, `api/` phục vụ xử lý. | Chọn `web/` nếu bạn tìm nút hoặc màn hình. Chọn `api/` nếu bạn tìm cách phân tích và che. |
| [`apps/web/`](apps/web/) | Giao diện React chạy trên trình duyệt. Nhận văn bản, đọc chữ trong PDF, hiển thị vùng cần che và tải kết quả. | [`App.tsx`](apps/web/src/App.tsx) để xem màn hình chính. [`SourcePanel.tsx`](apps/web/src/SourcePanel.tsx) và [`pdfDocument.ts`](apps/web/src/pdfDocument.ts) để xem phần nhập. [`useReview.ts`](apps/web/src/useReview.ts) để xem trạng thái rà soát. |
| [`apps/api/`](apps/api/) | Backend FastAPI. Nhận yêu cầu phân tích, kiểm dữ liệu, gọi bộ nhận diện và tạo văn bản đã che. | [`controllers.py`](apps/api/controllers.py) chứa các endpoint. [`schemas.py`](apps/api/schemas.py) định nghĩa dữ liệu. [`analysis.py`](apps/api/services/analysis.py) chọn phương pháp, [`redaction.py`](apps/api/services/redaction.py) thay đoạn đã duyệt. |
| [`ml/`](ml/) | Mã học máy và đánh giá. Huấn luyện CRF tiếng Việt, nạp trọng số và đo độ chính xác. `ml/upstream/` chứa mã chạy đối chứng ba công cụ tiếng Anh. | [`train.py`](ml/train.py), [`model.py`](ml/model.py), [`scoring.py`](ml/scoring.py) và [`evaluate.py`](ml/evaluate.py). |
| [`data/`](data/) | Nguồn dữ liệu giả lập. Tiếng Việt chia `train` để huấn luyện, `validation` để chọn cấu hình và `test` để chấm. `english.jsonl` dùng cho đối chứng tiếng Anh. | [`train-validation-manifest.json`](data/train-validation-manifest.json), [`test-manifest.json`](data/test-manifest.json) và [mô tả tập tiếng Anh](data/english.md). |
| [`artifacts/`](artifacts/) | Đầu ra do chương trình tạo. `model/` chứa trọng số và thông tin mô hình. `evaluation.json` tổng hợp điểm mà trang Thực nghiệm đọc qua API. | [Thông tin mô hình](artifacts/model/metadata.json) và [kết quả tổng hợp](artifacts/evaluation.json). |
| [`tests/`](tests/) | Test Python cho backend, xử lý định danh, mô hình, cách tính điểm và bảo vệ dữ liệu. Test chạy trên trình duyệt nằm riêng ở `apps/web/e2e/`. | [`test_api_contract.py`](tests/test_api_contract.py), [`test_privacy.py`](tests/test_privacy.py), [`test_evaluation.py`](tests/test_evaluation.py) và [test nhập PDF](apps/web/e2e/pdf-import.spec.ts). |
| [`scripts/`](scripts/) | Lệnh hỗ trợ kiểm tra và tái tạo. Dùng để kiểm giới hạn mã nguồn, tạo PDF demo, cài và chạy ba công cụ đối chứng. | [`check_source.py`](scripts/check_source.py), [`generate-demo-pdf.py`](scripts/generate-demo-pdf.py), [`setup-upstream.ps1`](scripts/setup-upstream.ps1). |
| [`docs/`](docs/) | Hướng dẫn sử dụng, kiến trúc, báo cáo, tiến độ và biên bản QA. `docs/evidence/` có file mẫu và file đã tải từ web. `docs/reviews/` chứa kết quả nghiệm thu theo phạm vi. | [Hướng dẫn nhập PDF](docs/huong-dan-nhap-pdf.md), [sơ đồ kiến trúc](docs/architecture.md), [báo cáo thực nghiệm](docs/experiment.md) và [tiến độ](docs/progress.md). |
| [`specs/`](specs/) | Đặc tả tính năng và danh sách công việc theo Spec Kit. Dùng để tra yêu cầu và tiêu chí trước khi sửa code. | [Đặc tả MedShield](specs/001-medical-redaction/spec.md) và [danh sách task](specs/001-medical-redaction/tasks.md). |
| [`.specify/`](.specify/) | Bộ mẫu tài liệu, nguyên tắc dự án và script của Spec Kit. Dùng khi phát triển tính năng. | [Constitution](.specify/memory/constitution.md). |
| [`.agents/`](.agents/) | Các hướng dẫn thao tác Spec Kit dành cho agent, từ đặc tả đến triển khai. | [Hướng dẫn triển khai Spec Kit](.agents/skills/speckit-implement/SKILL.md). |

Các file ở gốc thường gặp:

- [`AGENTS.md`](AGENTS.md) ghi quy ước sửa code, phân công và kiểm thử.
- [`THIRD_PARTY.md`](THIRD_PARTY.md) ghi nguồn, phiên bản và giấy phép của phần tái sử dụng.
- [`pyproject.toml`](pyproject.toml) và [`uv.lock`](uv.lock) khai báo và khóa môi trường Python. Frontend có cặp tương ứng [`package.json`](apps/web/package.json) và [`package-lock.json`](apps/web/package-lock.json).
- [`.env.example`](.env.example) là mẫu cấu hình. [`.gitignore`](.gitignore) loại các tệp cục bộ khỏi Git. [`.gitattributes`](.gitattributes) giữ đúng định dạng, gồm byte PDF khi checkout trên Windows.

## Code chạy theo đường nào?

1. **Nhập PDF:** `SourcePanel.tsx` mở trình chọn tệp. `usePdfImport.ts` quản lý việc chọn trang và hủy thao tác. `pdfDocument.ts` trích chữ tại trình duyệt bằng PDF.js.
2. **Phân tích:** `useReview.ts` gửi phần chữ tới `/api/analyze`. `controllers.py` gọi `analysis.py`. Các adapter trong `apps/api/adapters/` nhận diện bằng quy tắc hoặc mô hình CRF trong `ml/model.py`.
3. **Rà soát và xuất:** Sau khi bạn chỉnh vùng che, frontend gọi `/api/redact`. `redaction.py` thay đoạn đã chọn bằng ký hiệu như `[NAME_1]`. Khi bạn xác nhận, giao diện cho tải TXT hoặc JSON.

## Chạy nhanh trên Windows

Mở hai cửa sổ PowerShell từ thư mục repo. Cần `uv`, Node.js 24 và npm.

**Cửa sổ API**

```powershell
uv sync --locked --python 3.11.7
uv run --locked uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

**Cửa sổ web**

```powershell
Set-Location apps/web
npm ci
npm run dev
```

Mở [http://127.0.0.1:5173/](http://127.0.0.1:5173/). Dùng [PDF bệnh án giả lập](docs/evidence/demo-benh-an-ngoai-tru.pdf) để thử nhập trang 1–2. Xem [kịch bản demo ba phút](docs/huong-dan-nhap-pdf.md) để thực hành sửa một vùng bỏ sót và đối chiếu file đã tải.

Phạm vi nhập PDF có lớp chữ và xuất TXT/JSON đã qua nghiệm thu. OCR, xuất lại PDF giữ bố cục, Three.js và các hạng mục bàn giao toàn dự án có phạm vi riêng. Xem [biên bản PDF](docs/reviews/G4-pdf.md) và [bảng tiến độ](docs/progress.md).
