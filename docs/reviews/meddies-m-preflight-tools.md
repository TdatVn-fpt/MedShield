# Review độc lập công cụ chuẩn bị Phase M.1

Ngày 27/11/2026. Agent Dev/Tech Lead `/root` tích hợp công cụ. Reviewer là agent QA `/root/qa`. Phạm vi gồm nạp train v3, chia dữ liệu nội bộ, tách từ, chuyển BIO qua cửa sổ BPE và kiểm mẫu số strict. Bằng chứng gồm số tổng hợp trên train v3 của benchmark synthetic độc lập, học thuật và fixture riêng.

| Tệp được review | SHA-256 |
|---|---|
| `ml/meddies_m_preflight.py` | `d164de8ff6f3e517597f8c2d259dd3cd3666abcee5cf27dd43b3b711f297f26a` |
| `ml/meddies_m_preflight_data.py` | `d4241eae236ce69a60cfe7cd71d58de42c2cfd2de931a57036d070ec58aad832` |
| `ml/meddies_m_segment.py` | `51c85746fea4cd90f603abe2349ea80c3b97457b09a9208b2a1237a0688bb562` |
| `ml/meddies_m_features.py` | `c608b699abe72120000f92fe0f6bdd5c46fff359acf0c2e3a8ff11569702de32` |
| `tests/test_meddies_m_preflight_data.py` | `469d8defbf3c5080464bf48c06e2794e8fd78a1e2645b953498d9aef9b5373b3` |
| `tests/test_meddies_m_features.py` | `31f23f3f23517460aab904b632fd78b5b8d58a9cd4102173739e10aa2e559951` |

## Kiểm tra và kết quả

| Tiêu chí | Kết quả QA |
|---|---|
| Nguồn đầu vào đã duyệt | Hai bản manifest v3 công khai trong repo và cục bộ trùng byte, SHA-256 `b3f565aaa37dea425b7fc731d364afdb25e953021105247d521f8223cacec9f3`. Pool train khớp SHA-256 `b943bf1f039cd01a19486aa89dd543c50d9e75f7a60565f7bfe2e75022af631b`. Theo vết đọc tệp ở hai lượt gọi loader thật ghi nhận mỗi lượt đọc manifest rồi đúng pool v3. |
| Chặn báo cáo tự khai | Ca thử ban đầu cho thấy manifest tự tạo có thể xác nhận một fixture khác. Bản sửa ghim đúng hash manifest v3. QA chạy lại với manifest tự khai khớp fixture và xác nhận loader dừng trước khi đọc pool. Dùng manifest v3 với nội dung pool fixture cũng bị từ chối vì sai hash. |
| Phân chia và tương thích biên | Seed 20261127 tạo 64 ghi chú fit và 24 ghi chú validation nội bộ, rời nhau theo ID và lặp lại đúng khi đổi vị trí manifest cùng byte. Số vùng hai tập lần lượt 453 và 204. Có 3 và 10 vùng được cắt khoảng trắng ngoài trong bộ nhớ. Test kiểm mã trùng, thứ tự dòng và Unicode tổ hợp. Chưa kiểm chứng được phân nhóm bệnh nhân hoặc họ mẫu từ dữ liệu nguồn. |
| Tách từ và BPE | Smoke VnCoreNLP cục bộ trên ba fixture trả đủ 3 ghi chú, có 6/6/5 từ theo thứ tự và phủ các code point ngoài khoảng trắng. Smoke tích hợp với từ điển và mã BPE ViHealthBERT đã cache tại revision `f89e80b461e86f9cfc1c84019bd819830c24b6c5` dùng Transformers 4.57.3 ngoại tuyến, tạo 12 từ và một cửa sổ, giải mã vùng DOB khớp đúng biên nguồn. Test kiểm thêm NBSP hẹp, dấu tổ hợp rời, vùng cắt qua từ, từ vượt cửa sổ và quy tắc mỗi từ có một vị trí dự đoán. |
| Mẫu số strict | Kiểm `_predict` với fixture một ghi chú không có cửa sổ vẫn trả khóa ghi chú và danh sách dự đoán rỗng. Scorer đóng băng giữ 1 ghi chú, support 1 và FN 1. Mask loại vùng không khớp biên từ khỏi loss. Scorer tính các vùng đó trong validation nội bộ. |

## Lệnh đã chạy

```powershell
$qaPilotPaths = @('ml/meddies_m_preflight.py', 'ml/meddies_m_preflight_data.py', 'ml/meddies_m_segment.py', 'ml/meddies_m_features.py', 'tests/test_meddies_m_preflight_data.py', 'tests/test_meddies_m_features.py')
Get-FileHash -LiteralPath $qaPilotPaths
uv run --locked ruff check @qaPilotPaths
uv run --locked ruff format --check @qaPilotPaths
uv run --locked mypy @qaPilotPaths
uv run --locked pytest -q tests/test_meddies_m_preflight_data.py tests/test_meddies_m_features.py
uv run --locked python scripts/check_source.py
uv run --locked python -X utf8 -m ml.meddies_m_preflight --help
```

Ruff đạt cả lint và format trên sáu tệp, mypy không báo lỗi, 11 test qua, kiểm source có 0 vi phạm và CLI hiển thị trợ giúp thành công. QA chạy kiểm loader, Java và mẫu số bằng `uv run --locked python -X utf8 -`. Ca từ điển và BPE dùng `uv run --offline --locked --with transformers==4.57.3 python -X utf8 -` và chế độ `local_files_only=True`.

## Kết luận và giới hạn

**PASS phạm vi chuẩn bị công cụ Phase M.1.** Kết quả chạy thử ở đây chỉ bao gồm đếm dữ liệu và fixture kỹ thuật. QA dùng tệp tokenizer cục bộ, chưa tải trọng số hay chạy fine-tune. Train v3 là nguồn duy nhất cho lần kiểm dữ liệu thật. Chưa có số F1, CI hoặc đánh giá cổng mô hình từ công việc này. Pilot cập nhật trọng số chờ gói phân xử theo [giao thức Phase E](../meddies-silver.md) và [quyết định checkpoint](../decisions/phase-m-checkpoints.md).
