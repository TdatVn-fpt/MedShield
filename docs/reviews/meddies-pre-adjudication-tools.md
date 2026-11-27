# Review độc lập công cụ trước phân xử Meddies

Ngày 27/11/2026. Tác giả thay đổi công cụ là agent Dev/Tech Lead `/root`. Reviewer là agent QA `/root/qa`. Phạm vi thuộc E1–E3, gồm tiếp nhận phiếu rà train, tính IAA và xuất gói phân xử. Review dùng fixture giả lập riêng cùng phiếu rà đã duyệt và mẫu train đi kèm.

| Tệp được review | SHA-256 |
|---|---|
| `ml/meddies_silver.py` | `d6c9f55fc02182a79165d586bcf816b5f9772352ece041d3570186530eab14b2` |
| `ml/meddies_agreement.py` | `c63c414baac83234465bf3a57dfcd030efe802b47c746e38e094641ff3f752` |
| `ml/meddies_review_receipt.py` | `e94908f432e595f3e151ee5994d0a2252930ce6408ffbfbdb69836562a1c595f` |
| `tests/test_meddies_silver.py` | `d10a981b52585e12c1084c9417d6115bb81d9447228ca80b8afbf1144e3d4951` |

## Kiểm tra và kết quả

| Tiêu chí | Kết quả QA |
|---|---|
| Tiếp nhận nguyên bản phiếu chủ dự án | Tệp đính kèm và bản dưới `step4` trùng byte, SHA-256 `f27c56d34aae804a3827278bf37eaf7036ce3fc906d54b28d076dd2b0903340e`. Mẫu có SHA-256 `f5d47d6a0dc09e43b47749a7310bf54c85253d3478c5b9051bf8fc53e0e69edf`, khớp manifest Bước 2. Công cụ đối chiếu đủ 100 quyết định theo nhãn, số mẫu, mã ghi chú và giá trị. Có 80 `ok`, 20 `needs_correction` gồm 5 NAME, 9 ADDR và 6 ID. Test từ chối giá trị bị đổi dạng Unicode và dòng cần sửa thiếu lý do. |
| Strict IAA và cổng theo tập | Fixture 149 validation cho TP 534, FN 360, F1 `178/238`, có 60 ghi chú bất đồng. Fixture 150 test gồm một lỗi biên và một lỗi nhãn cho TP 898, FP 2, FN 2, F1 `898/900`, có một ghi chú bất đồng. Cờ áp dụng cổng 0,85 chỉ bật trên test. Báo cáo có CI 95% bootstrap theo cặp ghi chú, 1.000 lượt, cho micro, từng nhãn và tỉ lệ bất đồng. Khoảng micro trên fixture test chứa điểm quan sát và đầu trên bằng 1. |
| Support tạm và định dạng phân xử | Fixture báo riêng support của từng lượt. A đủ support trên cả hai tập; B validation thiếu vùng theo ngưỡng, B test đủ. Các tệp gói chứa đúng 60 và 1 ghi chú bất đồng, với Unicode, CRLF và dấu tổ hợp nguyên vẹn. Hai bản nháp gắn đúng SHA-256 của từng gói, giữ phương án A/B tương ứng và đặt tất cả dòng `reviewed: false`. Báo cáo ghi `locked: false` và chưa sinh nhãn cuối. |
| Nguồn gốc lượt B | Fixture CLI từ chối sáu biến thể sai mô hình, revision, runtime, hash gói, hash hướng dẫn và hash prompt dù biên nhận hoàn tất được tính lại cho mỗi biến thể. SHA-256 hiện tại của manifest Bước 2 và Bước 3 khớp các hằng pin trong trình khóa. |
| Tập khóa lịch sử | SHA-256 của scorer `6f3f4e8b4c242c6f418003cb192a1dba967ad3161b0957a89adc9c3e5ab512c0`, `data/test.jsonl` `ad2dce2254e1eac809df51f5a827f64bfdb425babf1ca56cb5db87f7dea9bb96` và `data/test-manifest.json` `0b666c65fe50e80c6bbe478f9fbad82aba44ab91205962836b63e3a4db6aa91a` khớp mốc Phase Q. |
| Trình gán offline | Chromium chạy thành công hai ca kiểm thử mở gói, phục hồi bản nháp đúng hash, từ chối bản nháp sai hash, chọn vùng Unicode chính xác, bắt vùng chồng lấn và xuất sau khi hoàn tất rà soát ở 390 px. QA còn mở gói và bản nháp do Python sinh bằng Chromium ngoại tuyến ở 390 và 1440 px, xác nhận xuất bị khóa trước khi đánh dấu đã rà soát và JSONL xuất trùng nhãn/bounds của fixture. Các ca ngoại tuyến không phát request HTTP. |

## Lệnh đã chạy

```powershell
$paths = @('ml/meddies_silver.py', 'ml/meddies_agreement.py', 'ml/meddies_review_receipt.py', 'tests/test_meddies_silver.py')
uv run --locked ruff check @paths
uv run --locked ruff format --check @paths
uv run --locked mypy @paths
uv run --locked pytest -q tests/test_meddies_silver.py tests/test_phase_e_annotation.py tests/test_meddies_probe.py
uv run --locked python scripts/check_source.py
Get-FileHash -LiteralPath 'ml/scoring.py','data/test.jsonl','data/test-manifest.json','artifacts/meddies-step2-mapping.json','artifacts/meddies-step3-dedup.json'
```

Từ `apps/web`, đã chạy `npm.cmd run test:e2e -- phase-e-annotation.spec.ts`.

Quan sát thực tế gồm Ruff đạt, bốn tệp đúng format, mypy không báo lỗi trên bốn tệp, 16 test Python qua, kiểm source có 0 vi phạm và 2 test Chromium qua. QA chạy thêm fixture độc lập qua `uv run --locked python -X utf8 -`, gọi trực tiếp `ml.meddies_silver.main` với các đối số CLI. Ca Python → Chromium dùng `node --input-type=module -` từ `apps/web` để gọi `write_adjudication_packets`, mở HTML cục bộ và kiểm nội dung tải xuống. Các fixture tạm đã được dọn sau kiểm tra.

## Kết luận

**PASS phạm vi kỹ thuật trước phân xử trên fixture và tiếp nhận phiếu rà train.** CLI nhận manifest do người chạy cung cấp, nên lượt thật phải dùng manifest Bước 3 đã ghim. Một lần CLI thất bại có thể còn tệp trung gian của split chạy trước. Khi bàn giao cần chạy thành công đủ hai split và có `review.json` trong cùng thư mục.

IAA, support và gói phân xử thật còn chờ kết quả hai lượt gán. Số liệu fixture chỉ xác nhận hành vi công cụ. Trạng thái Phase E và khóa silver tiếp tục theo [giao thức](../meddies-silver.md).
