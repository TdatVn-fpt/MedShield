# Môi trường thực tế — G0

Người thực hiện: DevOps agent. Trạng thái: READY_FOR_REVIEW; reviewer: Dev và QA.
Máy kiểm tra: Windows, PowerShell, `D:\Workspace\MedShield`, ngày 18/11/2026 (Asia/Saigon).

| Thành phần | Phiên bản / kết quả quan sát |
|---|---|
| Python hệ thống | 3.14.2; không dùng làm interpreter backend |
| Python có sẵn khác | 3.11.7 và 3.13.7 |
| Python backend thực tế | CPython 3.11.7 trong `.venv`; `uv sync --python 3.11` thành công |
| Lần thử Python 3.12 | Tải bằng `uv python install 3.12` (~20,9 MiB), dừng sau hơn 4 phút chưa hoàn tất; dùng bản 3.11.7 sẵn có để tránh chặn G0 |
| uv | 0.11.21 |
| Node.js / npm | 24.13.0 / 11.6.2 |
| Git | 2.51.2.windows.1 |
| GitHub CLI | 2.97.0; quyền GitHub do Tech Lead kiểm tra riêng |
| Docker CLI | 29.1.2; daemon chưa chạy, thiếu pipe `dockerDesktopLinuxEngine` |
| React / React DOM | 19.3.1 |
| Vite / plugin React | 8.3.8 / 6.3.0 |
| TypeScript | 5.9.3 |
| ESLint / typescript-eslint | 9.39.5 / 8.73.0 |
| Prettier | 3.10.1 |
| FastAPI / Uvicorn | 0.164.0 / 0.54.0 |
| sklearn-crfsuite / python-crfsuite | 0.5.0 / 0.9.12, import thành công trên CPU |
| pytest / httpx | 9.2.0 / 0.28.1 |
| Ruff / mypy | 0.17.5 / 1.20.2 |

## Các phép kiểm đã chạy

- `npm install` thành công, tạo `apps/web/package-lock.json`.
- `uv sync --python 3.11` thành công, tạo `uv.lock`, cài 39 package.
- TestClient `GET /health`: HTTP 200, `engines[0].status == unavailable` đúng skeleton.
- Import `sklearn_crfsuite` thành công; đây là smoke dependency, chưa phải mô hình NER đã huấn luyện.
- `npm run build`: thành công, TypeScript + Vite; 16 module, bundle JS khoảng 219,69 kB.
- `npm run lint`: thành công, không lỗi.
- `npm run format:check`: thành công.
- `python scripts/check_source.py`: `Source policy: 0 violation(s)`.
- `uv run ruff check apps/api scripts`, Ruff format và mypy: thành công sau khi định dạng checker.
- Docker daemon chưa khả dụng; không coi đây là bằng chứng đã chạy Compose.
- Skeleton `/health` công khai engine `medshield-rules/unavailable`; chưa có phân tích nghiệp vụ ở G0.
- `npm audit --omit=dev`: 0 lỗ hổng. Audit toàn bộ báo 11 high từ dependency dev `picomatch <=4.0.7`; registry hiện trả latest 4.0.7, chưa có bản vá. Không dùng `audit fix --force` để hạ Vite qua nhiều major. Theo dõi trước khi triển khai ngoài local.
- Starlette cảnh báo TestClient dùng httpx bị deprecated; smoke vẫn chạy thành công, chưa đổi client trong G0.

## Chạy skeleton

```powershell
uv sync --frozen
uv run uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
# Terminal thứ hai:
cd apps/web
npm ci
npm run dev
```

API `http://127.0.0.1:8000/health`, web `http://127.0.0.1:5173`.
Lockfile đã được ghi sau smoke; dùng `--frozen` để tái cài đúng phiên bản.
