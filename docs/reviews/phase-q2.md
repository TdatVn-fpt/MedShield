# Review độc lập Phase Q2

Ngày 25/11/2026. Người kiểm tra độc lập với tác giả Q2. **PASS cho cổng hồi quy Phase Q2 trên cây nội dung `69a92807f390301e3fc6e37f0772c5eeac1aca05`.** Cả 9 tiêu chí số đạt và các lỗi phát hiện trong review đầu đã được kiểm tra lại. Kết luận này chỉ áp dụng cho cổng Q2. Chưa có kết luận chất lượng Phase E hoặc Phase M.

## Cách kiểm tra

Tạo index Git tạm từ `HEAD`, đưa nội dung ứng viên hiện hành vào index tạm và trích `git archive` vào thư mục mới `artifacts/local/q2-review-final-2db41482/src`. Không đổi nhánh hay index chính. Cài môi trường từ lockfile trong thư mục đó, không dùng virtualenv hoặc kết quả test của tác giả. Dữ liệu benchmark là đúng hai bộ đã khóa, scorer được runner kiểm hash. Kiểm cả SHA-256 thô trong checkout hiện hành: `ml/scoring.py` `6f3f4e8b4c242c6f418003cb192a1dba967ad3161b0957a89adc9c3e5ab512c0`, `data/test.jsonl` `ad2dce2254e1eac809df51f5a827f64bfdb425babf1ca56cb5db87f7dea9bb96`, `data/test-manifest.json` `0b666c65fe50e80c6bbe478f9fbad82aba44ab91205962836b63e3a4db6aa91a`.

```powershell
uv run --locked pytest -q --maxfail=1
uv run --locked python scripts/check_source.py
uv run --locked python -m ml.phase_q2_benchmark --output ../independent-q2.json
uv run --locked python -m ml.phase_q2_archive --snapshot ../../phase-q-before-q2 --output ../independent-pre-q2-spans.json
```

Snapshot cuối chạy **216 test Python qua**, một cảnh báo deprecation đã có của Starlette, và **0 vi phạm chính sách mã nguồn**. Lệnh tạo lại dự đoán baseline trước Q2 kiểm hash năm module Phase Q và tái tạo archive SHA-256 `300a6510b944c250721ae39d1fc36540b6644f4e1a7842dccda35f4362e3eed2` theo chuẩn LF. Benchmark độc lập với 1.000 bootstrap theo ghi chú sinh đủ 12 kết quả, trùng toàn bộ đối tượng JSON với lượt chạy của tác giả `artifacts/local/phase-q2-reviewed-comparison.json`.

Tại `apps/web` trong snapshot, `npm.cmd ci --no-audit --no-fund` và `npm.cmd run test:e2e -- phase-q2-phone-review.spec.ts qa-g1.spec.ts` chạy riêng **5/5 Chromium trong 12,7 giây**. Chỉ thay cổng local trong hai cấu hình snapshot (web 15173, API 18000), không đổi mã hoặc test. Lượt này kiểm request thật, hàng chờ PHONE, sửa → xuất, phản hồi phân tích cũ, BOM, Unicode và TXT đang đọc bị vô hiệu. Các bài trình duyệt khác nằm ngoài lượt reviewer này.

## Bằng chứng cổng hồi quy

| Tập | Rules strict F1 | CRF strict F1 | Hybrid strict F1 | Hybrid partial F1 | Hybrid ghi chú còn lộ | Hybrid ADDR strict F1 |
|---|---:|---:|---:|---:|---:|---:|
| Khóa gốc, 20 ghi chú | 40,00% → 74,07% | 53,33% → 53,33% | 53,06% → 84,75% | 57,14% → 84,75% | 55,00% → 25,00% | 40,00% → 100,00% |
| Mở rộng, 150 ghi chú | 70,69% → 81,00% | 46,35% → 46,35% | 81,45% → 90,51% | 85,28% → 92,34% | 60,67% → 31,33% | 40,00% → 77,78% |

Trên tập gốc, cả DOB lẫn PHONE đạt strict recall 100% ở Rules và Hybrid. ADDR Hybrid phục hồi bằng mức trước Phase Q. Cả ba chế độ đạt sàn không giảm quá 2 điểm trên tập mở rộng. Hybrid trên tập gốc có 25 TP, 1 FP, 8 FN, strict micro-F1 CI 95% là 70,18–94,92% và tỉ lệ ghi chú còn lộ 5/20 (CI 10,00–45,00%). Tập mở rộng do agent sinh chỉ dùng đo hồi quy. Chưa có tập đánh giá Phase E.

## Đánh giá mã và quan sát độc lập

- Hybrid hợp nhất ứng viên trước rồi chọn vùng không chồng lấn. Ngưỡng ADDR 0,75 và chính sách rule bao trọn lấn CRF đã bỏ. Vùng NAME/ADDR từ CRF được ưu tiên khi chưa có hiệu chuẩn đủ dữ liệu. DOB, ID và PHONE có từ dẫn được ưu tiên, PHONE đứng một mình giữ điểm cộng và nguồn hàng chờ riêng. Ngữ cảnh rõ thắng lỗi lịch hoặc cấu trúc căn cước trong ca đã kiểm. Refine cắt dấu ngoài vùng và giữ offset code point.
- Trong các test Q2 mới và phần thêm vào test cũ, không thấy chép giá trị thực thể từ test khóa để chỉnh rules. Ca kho `0900000041` đã có trong suite Phase Q trước lượt Q2. Từ khóa ngữ cảnh của những ca kiểm chung xuất phát yêu cầu, không phải nhãn hoặc định danh được sao chép từ tập khóa. Không dùng số liệu test khóa để chọn ngưỡng.
- Review đầu trên cây `166ac269cefad077cc739636c97627fba15661b9` tìm được ba nhóm lỗi từ probe độc lập: bộ lọc hình dạng ngày bỏ nhầm số sau neo liên hệ, dấu chấm làm mất từ dẫn viết tắt, và cụm danh từ `học sinh năm` làm phát sinh DOB. Snapshot cuối chạy lại đúng: `Máy lẻ liên hệ: 12-34-56.`, `Hotline: 14-25-90.` và `ĐT. cá nhân: 718 399.` đều có PHONE đúng nguyên văn; `Học sinh năm 2021 được khám định kỳ.` không tạo DOB. Câu kiểm lân cận `Học sinh được sinh năm 2006, tái khám ngày mai.` vẫn nhận DOB `2006`. Ca ngày sai lịch có neo nhận giá trị nguyên văn, không nhận phần hẹn khám.

Các probe trên do reviewer soạn để kiểm hành vi theo đặc tả, không lấy từ bộ khóa. Để hiệu chuẩn ngưỡng theo nhãn còn cần validation độc lập đủ support và họ mẫu; lượt này không xác nhận ngưỡng đã được hiệu chuẩn hay mức giảm rủi ro trên bệnh án thật.
