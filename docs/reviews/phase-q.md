# Biên bản kiểm tra độc lập Phase Q

**Kết luận Phase Q: CHANGES_REQUESTED.** Ngày 25/11/2026, kiểm tra checkout `feat/medshield-demo` với baseline `773cead6eea623a345e1e1fa6b5732a8b2b6ae77`. Trên tập khóa gốc, hai nhãn DOB và PHONE của Rules vẫn có F1 bằng 0%. ADDR trong Hybrid cũng giảm trên cả hai tập. Quy trình đo đã tái tạo được. Điều kiện của chủ dự án yêu cầu dừng trước Phase M. Biên bản này chỉ kết luận về Phase Q.

## Phép kiểm độc lập

- `git diff --exit-code -- ml/scoring.py data/test.jsonl data/test-manifest.json` trả 0. `Get-FileHash -Algorithm SHA256 ml/scoring.py,data/test.jsonl,data/test-manifest.json` khớp ba mã đóng băng, lần lượt là `6f3f4e8b4c242c6f418003cb192a1dba967ad3161b0957a89adc9c3e5ab512c0`, `ad2dce2254e1eac809df51f5a827f64bfdb425babf1ca56cb5db87f7dea9bb96` và `0b666c65fe50e80c6bbe478f9fbad82aba44ab91205962836b63e3a4db6aa91a`.
- Tái tạo cả 12 hàng trong bộ nhớ bằng `ml.phase_q_benchmark`: xác thực digest, nạp hai tập, chạy phân tích tại baseline và checkout hiện tại trên ba chế độ, rồi chấm với scorer khóa. Kết quả, metadata engine, phân loại lỗi và manifest của cả 12 hàng khớp chính xác [artifact Phase Q](../../artifacts/phase-q-comparison.json). Các chỉ số micro và theo nhãn của ba hàng baseline tập gốc cũng khớp chính xác `git show 773cead:artifacts/evaluation-vi.json`.
- `uv run --locked pytest -q tests/test_phase_q_rules.py tests/test_phase_q_benchmark.py tests/test_phase_q_hybrid.py` qua 127/127 ca. Chạy riêng bộ hồi quy gốc với `uv run --locked pytest -q --ignore=tests/test_phase_q_rules.py --ignore=tests/test_phase_q_benchmark.py --ignore=tests/test_phase_q_hybrid.py` qua 55/55 ca. FastAPI/TestClient có một cảnh báo deprecation. Các phép kiểm độc lập ở đây chạy Python. Bằng chứng Chromium do nhóm triển khai ghi riêng.

| Tập test tiếng Việt | Rules trước → sau | CRF trước → sau | Hybrid trước → sau |
| --- | ---: | ---: | ---: |
| Khóa gốc, 20 ghi chú / 33 vùng vàng | 4,76% → 40,00% | 53,33% → 53,33% | 52,00% → 53,06% |
| Mở rộng, 150 ghi chú / 560 vùng vàng | 32,00% → 70,69% | 46,35% → 46,35% | 62,75% → 81,45% |

Bảng dùng micro-F1 exact span + label. Tập mở rộng là dữ liệu giả lập, `participant_reviewed_count = 0`.

## Phát hiện cần xử lý

1. **DOB và PHONE trên test khóa gốc.** Bốn vùng vàng PHONE dùng số tổng hợp ngoài cấu trúc điện thoại Việt Nam, gồm `+84 000 000 021` và `000 000 0022`. Chúng không qua bộ kiểm tra số Việt Nam hiện hành. Bốn vùng vàng DOB nằm sau các cụm hành chính như “ngày sinh ghi đúng là”, “đổi năm sinh trong hồ sơ từ … thành …” và “năm sinh của trẻ là”. Recognizer hiện tại chỉ hỗ trợ những mẫu từ dẫn gần giá trị hơn. Không dùng các ví dụ trên làm fixture phát triển.
2. **ADDR trong Hybrid.** Trên test gốc, F1 giảm từ 100% xuống 40% (TP/FP/FN từ 3/0/0 xuống 1/1/2). Trên test mở rộng, F1 giảm từ 77,78% xuống 40% (70/20/20 xuống 30/30/60). Đối chiếu ứng viên trên test gốc cho thấy hai span CRF đúng có score khoảng 0,7114 và 0,4948, đều dưới ngưỡng ADDR 0,75. Rules chỉ bù lại một span có biên dư. Điểm tổng tăng trong khi khả năng che địa chỉ giảm.
3. **Ca mô phỏng ngoài hai tập test.** `recognize("Hoc sinh 1990 co lich kham.", "vi")` nhận nhầm `1990` thành DOB vì cho phép từ dẫn `sinh` đứng đơn lẻ trước một năm. `recognize("Ngay sinh: 1/2-1998.", "vi")` chấp nhận dấu phân tách lẫn lộn. `recognize("Dien thoai: 090 123 4567 99.", "vi")` đề xuất phần đầu của chuỗi số. Ca PHONE cần xác định rõ ở guideline khi nào nhóm số sau cùng là phần mở rộng hoặc dữ liệu kế tiếp.

## Quyết định đề nghị

Chốt cách diễn giải số giả lập ngoài dải trong tập khóa gốc với chủ dự án. Giữ bytes và kết quả của tập gốc để đối chiếu lịch sử. Nếu muốn đo riêng trên số đúng cấu trúc, định nghĩa tập giả lập bổ sung và công bố kết quả song song. Dùng thêm họ validation độc lập để kiểm thử từ dẫn DOB hành chính và lựa chọn ngưỡng ADDR. Chỉ đánh giá lại sau khi đã khóa quy tắc và ngưỡng trên validation. Phase M và L tiếp tục chờ điều kiện của Phase Q.
