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

## G2 · T204 — Cài lại và chạy engine CRF chính

DevOps · READY_FOR_REVIEW. Đây là bằng chứng cài lại và suy luận độc lập trên Windows x64, PowerShell 5.1, uv 0.11.21 và CPython 3.11.7. Dùng cửa sổ PowerShell riêng từ gốc checkout. Để lặp lại từ môi trường trống, chọn hậu tố mới cho cả venv lẫn thư mục model nếu các đường dẫn của lần kiểm dưới đây đã tồn tại.

### Cài từ lock và huấn luyện

```powershell
$env:UV_PROJECT_ENVIRONMENT="$PWD/.venv-g2-t204-final"
if (Test-Path -LiteralPath $env:UV_PROJECT_ENVIRONMENT) { throw 'Expected a fresh T204 environment.' }
$out='artifacts/local/t204-reinstall-model-final'
if (Test-Path -LiteralPath $out) { throw 'Expected a fresh T204 model directory.' }
$lockBefore=(Get-FileHash uv.lock -Algorithm SHA256).Hash
$testBefore=(Get-FileHash data/test.jsonl -Algorithm SHA256).Hash
uv sync --locked --python 3.11.7 --link-mode copy
if ($LASTEXITCODE) { throw 'T204 command failed.' }
& .venv-g2-t204-final/Scripts/python.exe -B -m ml.train --data-dir data --output-dir $out
if ($LASTEXITCODE) { throw 'T204 command failed.' }
if ((Get-FileHash uv.lock -Algorithm SHA256).Hash -ne $lockBefore) { throw 'Lock changed during the run.' }
if ((Get-FileHash data/test.jsonl -Algorithm SHA256).Hash -ne $testBefore) { throw 'Test split changed during the run.' }
"lock_sha256=$($lockBefore.ToLowerInvariant())"
"test_sha256=$($testBefore.ToLowerInvariant())"
```

uv tạo venv mới, resolve 42 package từ lock và cài 39 package cho Windows. Các bản thực tế gồm `python-crfsuite==0.9.12`, `sklearn-crfsuite==0.5.0` và `scikit-learn==1.9.1`. `uv sync --locked` và lệnh huấn luyện đều exit 0. Train dùng revision `medshield-vi-synthetic-v2`, 60 ghi chú train và 20 ghi chú validation. SHA-256 của manifest train/validation là `f563a77d75eda26cb1b67a73753fd47596ce66b2685522103874442cbc4d6bcc`.

`uv.lock` có SHA-256 `40a8044ab62c53151ffd923cd450bdc993b62f923ef069a9e8a10d2e838ee8cf` trước và sau lần chạy. Tập test tiếng Việt giữ SHA-256 `ad2dce2254e1eac809df51f5a827f64bfdb425babf1ca56cb5db87f7dea9bb96`. Trọng số mới có revision `sha256:8f0ee850c659b7c13d23280cad1a7c88c1fd051dc462ca5188810d392a7bce3f` và trùng SHA-256 với artifact đã công bố tại thời điểm đối chiếu.

### Nạp lại và suy luận trong tiến trình riêng

Lệnh dùng đúng model vừa huấn luyện. TestClient gọi ASGI qua `/health` và `/api/analyze` với một ghi chú giả lập có BOM, emoji, dấu tổ hợp và CRLF. Kết quả JSON chỉ in revision và vị trí.

```powershell
$env:MEDSHIELD_MODEL_DIR="$PWD/artifacts/local/t204-reinstall-model-final"
@'
import hashlib
import json
import os
from importlib.metadata import version
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import app

directory = Path(os.environ["MEDSHIELD_MODEL_DIR"])
revision = "sha256:" + hashlib.sha256((directory / "model.crfsuite").read_bytes()).hexdigest()
name = "Nguye\u0302\u0303n A\u0301nh"
phone = "0901234567"
note = f"\ufeff\U0001f642\r\nNg\u01b0\u1eddi b\u1ec7nh {name}.\r\n\u0110i\u1ec7n tho\u1ea1i {phone}.\r\n"
results = {}
with TestClient(app) as client:
    health = client.get("/health")
    assert health.status_code == 200
    for mode in ("ner", "hybrid"):
        response = client.post("/api/analyze", json={"text": note, "language": "vi", "mode": mode})
        assert response.status_code == 200, response.status_code
        data = response.json()
        assert data["engine"]["mode"] == mode
        assert data["engine"]["model_revision"] == revision
        spans = [
            (item["start"], item["end"], item["label"], item["source"]) for item in data["entities"]
        ]
        name_start = note.index(name)
        phone_start = note.index(phone)
        assert (name_start, name_start + len(name), "NAME", "medshield-crf") in spans, spans
        assert data["redacted_text"].startswith("\ufeff\U0001f642\r\n")
        assert data["redacted_text"].count("\r\n") == note.count("\r\n")
        if mode == "hybrid":
            assert (phone_start, phone_start + len(phone), "PHONE", "medshield-rules") in spans, spans
        results[mode] = spans
print(json.dumps({
    "revision": revision,
    "native": version("python-crfsuite"),
    "health": health.status_code,
    "positions": results,
}))
'@ | & .venv-g2-t204-final/Scripts/python.exe -B -
if ($LASTEXITCODE) { throw 'T204 inference failed.' }
```

Lệnh trên exit 0. `/health`, `vi/ner` và `vi/hybrid` đều HTTP 200. NER trả `NAME [15,28)` từ `medshield-crf`. Hybrid dùng cùng revision, giữ vùng NAME và thêm `PHONE [42,52)` từ `medshield-rules`. Kiểm tra xác nhận BOM, emoji và CRLF còn nguyên trong bản che. Starlette phát một cảnh báo deprecation liên quan đến TestClient/httpx.
