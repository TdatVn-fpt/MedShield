# Review độc lập ánh xạ lại tập train Meddies

Ngày 27/11/2026. Tác giả mapper là agent Research/ML `/root/research_ml`. Reviewer là agent QA `/root/qa`. Phạm vi E1–E3, bản `step4-remapped-v3`, trên dữ liệu train của benchmark synthetic độc lập, học thuật.

| Tệp bằng chứng | SHA-256 |
|---|---|
| `ml/meddies_train.py` | `eef1236dd973cc8dbf0a6292cd13763ec3c3b36f54b95cb094a5d32c8d976119` |
| `ml/meddies_mapping_rules.py` | `ca1419a49cd09697438796cb36f0a8678e6e5dea0716faa7d096d4bac58a2134` |
| `tests/test_meddies_mapping_rules.py` | `5f04c1ff9ce57bc979a71b5a6e59ba4223f20690df2955f5d8e1d588b3057a7a` |
| `artifacts/local/meddies/step4-remapped-v3/provisional-train.jsonl` | `b943bf1f039cd01a19486aa89dd543c50d9e75f7a60565f7bfe2e75022af631b` |
| `artifacts/local/meddies/meddies-step4-remapped-v3.json` | `b3f565aaa37dea425b7fc731d364afdb25e953021105247d521f8223cacec9f3` |

## Đối chiếu cả tập

So sánh tuần tự train Bước 2 đã ghim và train v3. Cả 22.310 ghi chú giữ nguyên mã, thứ tự, văn bản Unicode và mọi biên DOB/PHONE. QA kiểm không có span mới, span vượt biên, span chồng lấn hay vùng vừa chỉnh bị thêm khoảng trắng ngoài. Chạy riêng bộ quy tắc trên từng dòng cũ để đối chiếu lại các bộ đếm trong manifest.

| Nhãn | Vùng trước | Vùng sau | Loại | Cắt biên |
|---|---:|---:|---:|---:|
| NAME | 45.978 | 45.971 | 7 | 6.960 |
| DOB | 7.474 | 7.474 | 0 | 0 |
| PHONE | 39.222 | 39.222 | 0 | 0 |
| ID | 56.386 | 51.327 | 5.059 | 2.589 |
| ADDR | 29.173 | 23.867 | 5.306 | 0 |
| **Tổng** | **178.233** | **167.861** | **10.372** | **9.549** |

ADDR loại 5.094 vùng cơ sở y tế và 212 vùng IP. ID loại 4.144 mã đơn/phiếu, 373 vùng tham chiếu và 542 mã ngoài phạm vi cá nhân. Có 556 lần cắt nhãn trường ID và 2.043 lần cắt tiền tố `BHYT-`, trong đó 10 vùng áp dụng cả hai luật. Không có ID chỉ gồm nhãn trường phải loại. Đối chiếu các cột HL7 nhắm đến số đơn ORC/OBR, trường điều khiển bản tin MSH/MSA, trường cơ sở MSH và khoảng tham chiếu OBX với định nghĩa chuẩn. [HL7 v2.5.1, chương 4](https://www.hl7.eu/HL7v2x/v251/std251/ch04.html) · [chương 2](https://hl7.eu/HL7v2x/v251/std251/ch02.html) · [chương 7](https://www.hl7.eu/HL7v2x/v251/std251/ch07.html)

Đối chiếu lại từng mục trong phiếu do chủ dự án duyệt với vùng của đúng ghi chú trong hai bản train. Có 80/80 vùng `ok` giữ nguyên. Trong 20 vùng `needs_correction`, mapper cắt biên 5 NAME và 2 ID, loại 9 ADDR và 4 ID. Đây là lần kiểm lại mẫu dùng hình thành luật. Phép đếm cả tập và đối chiếu phiếu có phạm vi cố định, không ước lượng CI hay chất lượng mô hình.

## Lệnh đã chạy

```powershell
$qaMappingPaths = @('ml/meddies_train.py', 'ml/meddies_mapping_rules.py', 'tests/test_meddies_mapping_rules.py', 'tests/test_meddies_intake.py')
uv run --locked ruff check @qaMappingPaths
uv run --locked ruff format --check @qaMappingPaths
uv run --locked mypy @qaMappingPaths
uv run --locked pytest -q tests/test_meddies_mapping_rules.py tests/test_meddies_intake.py tests/test_meddies_dedup.py
uv run --locked python scripts/check_source.py
Get-FileHash -LiteralPath $qaMappingPaths
```

Ruff và format đạt, mypy không báo lỗi trên bốn tệp, 28 test Python qua và kiểm source có 0 vi phạm. QA dùng `uv run --locked --with pyarrow==20.0.0 python -X utf8 -` để chạy đối chiếu cả tập và gọi `python -X utf8 -m ml.meddies_train` với shard đã ghim, `--private-output` và `--output` mới trong thư mục tạm bên dưới `artifacts/local/meddies`. Lần tái tạo độc lập kết thúc mã 0 và khớp SHA-256 của train, mẫu và manifest.

## Giới hạn

V3 còn 4.171 vùng có khoảng trắng ngoài do dữ liệu train Bước 2 mang theo, trên 1.639 ghi chú. Gồm 1.655 ID, 1.129 NAME, 879 PHONE và 508 ADDR. Kiểm tương thích trong bộ nhớ bằng cách giới hạn biên vào phần giá trị cho phép `ml.dataset.parse_note` đọc đủ cả 22.310 ghi chú. Chuẩn bị đầu vào Phase M cần xử lý biên tương thích và ghi số liệu của thao tác đó. Bản train được review giữ biên gốc ở những vùng này.

**PASS ánh xạ lại toàn bộ tập train v3 theo phiếu và luật đã chốt.** Chất lượng huấn luyện và tập đánh giá thuộc các bước đo riêng.
