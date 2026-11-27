# Review độc lập Meddies · Bước 3

Ngày 26/11/2026. **PASS cho Bước 3, cô lập nguồn, khử trùng lặp và xuất gói mù.** Bước 4 gán nhãn chưa nằm trong phạm vi review. Gói hiện có trạng thái `awaiting_blind_annotation`; chưa khóa tập đánh giá, chưa có IAA hay điểm Phase M.

## Phép kiểm

Reviewer đọc `ml/meddies_overlap.py`, `ml/meddies_dedup.py`, `tests/test_meddies_dedup.py` và manifest tổng hợp. Phần đối chiếu gói mù chỉ xuất số lượng, tên trường, kiểu trường, hash và kết quả kiểm trùng mã. Không xuất văn bản, mã từng ghi chú, hoặc nhãn. Runner chỉ đọc `text` và `info` từ shard trong bước so ứng viên; không đọc nhãn nhà phát hành cho tập đánh giá. Kiểm cặp tên với số điện thoại/ngày sinh dùng nhãn đã ánh xạ của train để lập chỉ mục, rồi tìm cặp bề mặt trực tiếp trên văn bản ứng viên.

```powershell
$d = 'artifacts/local/meddies'
$tag = 'step3-qa-84aa32b2' # thay bằng tên chưa tồn tại khi chạy lại
uv run --locked --with pyarrow==20.0.0 python -X utf8 -m ml.meddies_dedup "$d/vietnamese.parquet" "$d/step2-reviewed/provisional-train.jsonl" "$d/$tag" "$d/$tag.json"
uv run --locked --with pyarrow==20.0.0 pytest -q tests/test_meddies_dedup.py tests/test_meddies_intake.py tests/test_meddies_split.py
uv run --locked ruff check ml/meddies_overlap.py ml/meddies_dedup.py tests/test_meddies_dedup.py
uv run --locked ruff format --check ml/meddies_overlap.py ml/meddies_dedup.py tests/test_meddies_dedup.py
uv run --locked mypy ml/meddies_overlap.py ml/meddies_dedup.py tests/test_meddies_dedup.py
```

11/11 test qua, Ruff và mypy qua. Lượt riêng tái tạo manifest [Meddies Bước 3](../../artifacts/meddies-step3-dedup.json) và hai gói đúng từng byte.

## Đối chiếu kết quả

- Train tạm có 22.310 ghi chú từ 13 giá trị `source`; nhóm giữ lại cho đánh giá có 299 ghi chú từ một nguồn lâm sàng riêng, chưa thấy trùng giá trị nguồn. Chỉ mục bề mặt không tìm thấy cặp NAME + PHONE hoặc NAME + DOB đủ điều kiện. Không có ứng viên bị loại bởi hai phép so này.
- Reviewer dùng thêm lượt tính độc lập bằng phép nhân ma trận thưa SciPy trên chỉ mục 5-gram và so digest văn bản nguyên bản giữa train và cả hai gói. Chấm 6.670.690 cặp, thu được 53 ứng viên có điểm tối đa bằng 0 và Jaccard lớn nhất `2/65`, khớp manifest; không có giao digest toàn văn. Ngưỡng đã dùng là **lớn hơn** 0,5; ca đúng bằng 0,5 có test riêng. Jaccard lớn nhất chéo validation/test báo cáo là `0,105263`.
- Hai gói UTF-8 LF chỉ có trường `note_id` và `text` dạng chuỗi, đủ 299 mã riêng biệt và không giao giữa các tập. Cả hai SHA-256 khớp manifest và bản tái tạo.

| Gói | Số dòng | SHA-256 |
|---|---:|---|
| `test-blind.jsonl` | 150 | `4df20fa76cbedebc7caf7df088d46f18393bd9dbdde37fe99af7fa38d30657d0` |
| `validation-blind.jsonl` | 149 | `413c791c1cca479dcf4528589233b7c72cf9f5869ec46fdf7d776fd122524c02` |

## Giới hạn còn lại

Kết luận không xác minh danh tính bệnh nhân hay họ mẫu. So bề mặt chỉ phát hiện cặp chứa tên đã được ánh xạ trong cùng ghi chú train, kết hợp với định dạng số hoặc ngày được hỗ trợ. Tên đổi dấu, đảo trật tự, hoặc cặp không có trong nhãn train có thể không bị phát hiện; điểm Jaccard thấp chỉ phản ánh mức trùng từ 5-gram. Chênh lệch độ dài p50 giữa train (1.156) và nhóm đánh giá (362 code point) là một khác biệt phân phối cần giữ khi báo cáo điểm sau này. Với quy trình chủ dự án duyệt, `silver-locked` và `human_llm` chỉ ghi khi hoàn thành gán mù, phân xử, kiểm support, IAA và khóa hash. PASS bước kỹ thuật này không thay cho các cổng đó.
