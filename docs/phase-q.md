# Phase Q — Kết quả và điều kiện dừng

Ngày 25/11/2026. **Nghiệm thu Phase Q chưa đạt.** Rules sau sửa còn DOB và PHONE bằng 0% trên test khóa gốc. Phase M và L chưa bắt đầu. G1–G3 vẫn có biên bản cho phiên bản gốc; thay đổi Phase Q ở những phạm vi này cần review riêng. G4 vẫn IN_PROGRESS, G5 vẫn TODO.

## 1. Việc đã làm

- **Q1.** Tách rules tiếng Việt trong `apps/api/adapters/vi_structured.py` và `vi_names_places.py`; nối vào `rules.py` và `analysis.py`. DOB kiểm lịch, PHONE kiểm libphonenumber cho vùng VN, ID có neo ngữ cảnh và kiểm dạng CCCD/CMND, hộ chiếu, BHYT, mã bệnh án. CCCD đối chiếu một năm sinh rõ ràng khi có; mã tỉnh hiện gồm danh sách trong nước, không bao phủ mã đăng ký ở nước ngoài. NAME và ADDR dùng từ dẫn và danh sách họ/địa danh làm tín hiệu. Khớp chữ không dấu trên bản ánh xạ và xuất offset nguyên văn. Thêm dependency vào `pyproject.toml`, `uv.lock` và nguồn vào `THIRD_PARTY.md`.
- **Q2.** Tên trùng nguyên văn sau lần phát hiện đủ điểm trong cùng ghi chú được đề xuất với nguồn riêng. Bản có khác chữ hoa hoặc ký tự tổ hợp không được xem là lần lặp chính xác. Áp dụng cho rules và hybrid tiếng Việt; khóa token và hợp đồng API giữ nguyên.
- **Q3.** Tạo bộ test riêng 150 ghi chú, 560 vùng vàng, 15 họ mẫu và 20 ca âm. `ml/phase_q_dataset.py` tái tạo từ seed 20261125. `ml/phase_q_benchmark.py` chạy phiên bản trước từ commit `773cead6eea623a345e1e1fa6b5732a8b2b6ae77`, dùng cùng CRF đã khóa và cùng scorer cho cả hai bản. Test mới do agent tạo và gán nhãn; `participant_reviewed_count = 0`. [Manifest](../data/phase-q-test-manifest.json)
- **Q4.** `apps/api/services/hybrid.py` hợp nhất CRF và rules. Rules đã kiểm dạng ưu tiên ở DOB/PHONE/ID, CRF ưu tiên ở NAME/ADDR, trừ khi rule cùng nhãn bao trọn và dài hơn. `ml/tune_hybrid.py` quét 243 tổ hợp trên 20 ghi chú validation, xếp theo macro-F2 rồi micro-F2; hòa thì giữ ngưỡng tổng thấp hơn. Chốt ADDR 0,75, bốn nhãn khác 0,0. Validation F2 micro 89,04%, không dùng để công bố điểm test. [Kết quả chọn ngưỡng](../artifacts/phase-q-thresholds.json)

## 2. Số liệu trước và sau

Mỗi ô là **Precision/Recall/F1 (%) (TP/FP/FN)**. Chấm strict theo đúng biên và nhãn trước sửa tay. CRF được giữ nguyên. Relaxed F1 thuộc Phase M. Kết quả tiếng Anh giữ riêng, không tính vào các bảng dưới. [Artifact đầy đủ](../artifacts/phase-q-comparison.json)

### Test khóa gốc · 20 ghi chú / 33 vùng vàng

| Chế độ | Nhãn | Trước | Sau |
|---|---|---:|---:|
| Rules | Micro | 11,11/3,03/4,76 (1/8/32) | 75,00/27,27/40,00 (9/3/24) |
| Rules | NAME | 0,00/0,00/0,00 (0/1/17) | 87,50/41,18/56,00 (7/1/10) |
| Rules | DOB | 0,00/0,00/0,00 (0/0/4) | 0,00/0,00/0,00 (0/0/4) |
| Rules | PHONE | 0,00/0,00/0,00 (0/4/4) | 0,00/0,00/0,00 (0/1/4) |
| Rules | ID | 100,00/20,00/33,33 (1/0/4) | 100,00/20,00/33,33 (1/0/4) |
| Rules | ADDR | 0,00/0,00/0,00 (0/3/3) | 50,00/33,33/40,00 (1/1/2) |
| CRF | Micro | 100,00/36,36/53,33 (12/0/21) | 100,00/36,36/53,33 (12/0/21) |
| CRF | NAME | 100,00/52,94/69,23 (9/0/8) | 100,00/52,94/69,23 (9/0/8) |
| CRF | DOB | 0,00/0,00/0,00 (0/0/4) | 0,00/0,00/0,00 (0/0/4) |
| CRF | PHONE | 0,00/0,00/0,00 (0/0/4) | 0,00/0,00/0,00 (0/0/4) |
| CRF | ID | 0,00/0,00/0,00 (0/0/5) | 0,00/0,00/0,00 (0/0/5) |
| CRF | ADDR | 100,00/100,00/100,00 (3/0/0) | 100,00/100,00/100,00 (3/0/0) |
| Hybrid | Micro | 76,47/39,39/52,00 (13/4/20) | 81,25/39,39/53,06 (13/3/20) |
| Hybrid | NAME | 100,00/52,94/69,23 (9/0/8) | 91,67/64,71/75,86 (11/1/6) |
| Hybrid | DOB | 0,00/0,00/0,00 (0/0/4) | 0,00/0,00/0,00 (0/0/4) |
| Hybrid | PHONE | 0,00/0,00/0,00 (0/4/4) | 0,00/0,00/0,00 (0/1/4) |
| Hybrid | ID | 100,00/20,00/33,33 (1/0/4) | 100,00/20,00/33,33 (1/0/4) |
| Hybrid | ADDR | 100,00/100,00/100,00 (3/0/0) | 50,00/33,33/40,00 (1/1/2) |

### Test mở rộng · 150 ghi chú / 560 vùng vàng

| Chế độ | Nhãn | Trước | Sau |
|---|---|---:|---:|
| Rules | Micro | 63,16/21,43/32,00 (120/70/440) | 89,13/58,57/70,69 (328/40/232) |
| Rules | NAME | 33,33/5,88/10,00 (10/20/160) | 100,00/34,12/50,88 (58/0/112) |
| Rules | DOB | 100,00/25,00/40,00 (20/0/60) | 85,71/75,00/80,00 (60/10/20) |
| Rules | PHONE | 87,50/58,33/70,00 (70/10/50) | 91,67/91,67/91,67 (110/10/10) |
| Rules | ID | 50,00/20,00/28,57 (20/20/80) | 100,00/90,00/94,74 (90/0/10) |
| Rules | ADDR | 0,00/0,00/0,00 (0/20/90) | 33,33/11,11/16,67 (10/20/80) |
| CRF | Micro | 85,58/31,79/46,35 (178/30/382) | 85,58/31,79/46,35 (178/30/382) |
| CRF | NAME | 91,53/63,53/75,00 (108/10/62) | 91,53/63,53/75,00 (108/10/62) |
| CRF | DOB | 0,00/0,00/0,00 (0/0/80) | 0,00/0,00/0,00 (0/0/80) |
| CRF | PHONE | 0,00/0,00/0,00 (0/0/120) | 0,00/0,00/0,00 (0/0/120) |
| CRF | ID | 0,00/0,00/0,00 (0/0/100) | 0,00/0,00/0,00 (0/0/100) |
| CRF | ADDR | 77,78/77,78/77,78 (70/20/20) | 77,78/77,78/77,78 (70/20/20) |
| Hybrid | Micro | 80,45/51,43/62,75 (288/70/272) | 87,65/76,07/81,45 (426/60/134) |
| Hybrid | NAME | 84,38/63,53/72,48 (108/20/62) | 93,15/80,00/86,08 (136/10/34) |
| Hybrid | DOB | 100,00/25,00/40,00 (20/0/60) | 85,71/75,00/80,00 (60/10/20) |
| Hybrid | PHONE | 87,50/58,33/70,00 (70/10/50) | 91,67/91,67/91,67 (110/10/10) |
| Hybrid | ID | 50,00/20,00/28,57 (20/20/80) | 100,00/90,00/94,74 (90/0/10) |
| Hybrid | ADDR | 77,78/77,78/77,78 (70/20/20) | 50,00/33,33/40,00 (30/30/60) |

SHA-256 trước và sau khớp nhau:

| File khóa | SHA-256 |
|---|---|
| `ml/scoring.py` | `6f3f4e8b4c242c6f418003cb192a1dba967ad3161b0957a89adc9c3e5ab512c0` |
| `data/test.jsonl` | `ad2dce2254e1eac809df51f5a827f64bfdb425babf1ca56cb5db87f7dea9bb96` |
| `data/test-manifest.json` | `0b666c65fe50e80c6bbe478f9fbad82aba44ab91205962836b63e3a4db6aa91a` |

## 3. Lỗi còn lại

Trên test gốc, hybrid có 18 FN không giao vùng và 2 FN lệch biên, 1 FP không giao vùng và 2 FP lệch biên. Trên test mở rộng, hybrid có 94 FN không giao vùng và 40 FN lệch biên, 20 FP không giao vùng và 40 FP lệch biên. Không ghi nhận sai nhãn trong hai kết quả hybrid. Rules trên test mở rộng có 202 FN không giao vùng, 30 FN lệch biên, 10 FP không giao vùng và 30 FP lệch biên.

Hai nguyên nhân kích hoạt điều kiện dừng trên test gốc:

- **PHONE:** Bốn vùng vàng là số giả lập dùng đầu không hợp lệ tại Việt Nam: `+84 000 000 021`, `000 000 0022`, `000.000.0023` và `000-000-0313`. Bộ kiểm số loại chúng đúng theo tiêu chí định dạng đã chọn. Tập mở rộng đạt PHONE F1 91,67%. Ca kho gốc `0900000041` được loại, nhưng cùng chuỗi vẫn bị bắt sai trong ngữ cảnh khác `vật tư lô` của test mới.
- **DOB:** Bốn vùng vàng nằm trong câu đính chính có nhiều từ xen kẽ hoặc hai năm cạnh nhau, ví dụ `ngày sinh ghi đúng là`, `đổi năm sinh trong hồ sơ từ … thành …` và `năm sinh của trẻ là`. Rules nhận ngày hợp lệ sau từ dẫn trực tiếp nhưng bỏ sót các cấu trúc này. Tập mở rộng đạt DOB F1 80,00%. Không dùng các ca test khóa để chỉnh vòng đo này.

| Loại | Tập và ID | Ví dụ giả lập | Giải thích |
|---|---|---|---|
| FN | Gốc · vi-test-001 | `+84 000 000 021` (PHONE) | Đầu số không hợp lệ. |
| FN | Gốc · vi-test-010 | `1971` (DOB) | Từ dẫn và năm bị ngăn bởi nội dung đính chính; cùng câu còn bỏ sót năm mới 1972. |
| FN | Mở rộng · vi-phase-q-011 | `12 đường Trăng Qua Suối, phường Mầm Trăng, TP. Cánh Diều` (ADDR) | Địa chỉ theo câu giao tận nhà, thiếu neo cư trú trực tiếp; hybrid không giữ đề xuất. |
| FN | Mở rộng · vi-phase-q-091 | `lê hà miên` (NAME) | Bản chép lời không có tên được nhận chắc chắn ban đầu để truyền lan. |
| FN | Mở rộng · vi-phase-q-081 | `P0000081` (ID) | Cụm `hộ chiếu thành` chen giữa từ dẫn và mã. |
| FP | Gốc · vi-test-002 | `bùi mộc nhiên theo số` (NAME) | Lấy thêm từ dẫn số điện thoại vào tên. |
| FP | Gốc · vi-test-013 | `ghi trên phiếu: 12 hẻm Hạt Nắng, …` (ADDR) | Rule lấy thêm phần mở đầu trường và bao trọn span CRF. |
| FP | Mở rộng · vi-phase-q-021 | `22 tháng 3 năm 2004` (DOB) | Dự đoán thiếu từ `ngày` thuộc biên vàng. |
| FP | Mở rộng · vi-phase-q-101 | `102/4 ngõ Mầm Ngô Non, P. Mầm Trăng, Q. Cánh Diều |` (ADDR) | Ăn thêm dấu phân cách cột. |
| FP | Mở rộng · vi-phase-q-131 | `0900000041` (PHONE) | Số đúng cấu trúc nhưng dùng làm mã lô. |

## 4. Kiểm thử và tái tạo

```powershell
uv run --locked pytest -q
uv run --locked ruff check apps/api ml tests
uv run --locked ruff format --check apps/api ml tests
uv run --locked mypy apps/api ml tests
uv run --locked python scripts/check_source.py
uv run --locked python -m ml.tune_hybrid
uv run --locked python -m ml.phase_q_benchmark --output artifacts/local/phase-q-recheck.json
uv run --locked python -m ml.evaluate --english artifacts/evaluation-en.json --output-dir artifacts/local/phase-q-recheck
```

Backend 182 test qua, gồm 55 test hiện có, 124 ca recognizer/truyền lan, 2 ca benchmark, 1 ca hybrid. Smoke hiện có đổi số điện thoại sai cấu trúc thành fixture hợp lệ để tiếp tục kiểm tra đúng mục tiêu inference. Ruff, mypy 44 file và kiểm tra 299 dòng đều qua. Lệnh benchmark dùng tên đầu ra mới và cần checkout có commit baseline ở trên.

Từ `apps/web/`, `npm.cmd run lint`, `npm.cmd run typecheck`, `npm.cmd run format:check`, `npm.cmd run build` và `npm.cmd run test:e2e` đều qua. Chromium qua 22/22 trong 44,3 giây, gồm request thật, sửa → xuất TXT/JSON, input mới vô hiệu kết quả cũ, 390px/1440px và Unicode. Ca trình duyệt thêm tay tên lặp kiểm tra cả nguồn đề xuất tự động, thao tác bỏ vùng và sau đó thêm lại bằng tay. WebGL fallback thuộc G4 và chưa nằm trong bộ test này.

## 5. Rủi ro và việc còn mở

- Hybrid ADDR giảm từ 100,00% xuống 40,00% trên test nhỏ và từ 77,78% xuống 40,00% trên test mở rộng. Chính sách cho rule bao trọn ghi đè CRF có thể chọn sai biên; 20 ghi chú validation chỉ có 10 ADDR, cùng một họ mẫu và không đủ để bảo vệ ngưỡng trên kiểu câu khác.
- Tổng micro-F1 phản ánh dữ liệu giả lập; 150 ghi chú có 15 họ mẫu, chưa có rà soát người dùng và chưa có bằng chứng trên bệnh án thật. Bản đo này chưa đủ để dùng cho quyết định tự động chia sẻ văn bản y tế.
- Danh sách địa danh phục vụ nhận diện chỉ gồm tỉnh/thành hiện hành và lịch sử cùng một số quận/huyện. Mã tỉnh lịch sử và cấu trúc căn cước tham chiếu hướng dẫn của Công an TP Hà Nội; đăng ký khai sinh ở nước ngoài cần bảng mã riêng. [Hướng dẫn cấu trúc số định danh](https://bocongan.gov.vn/bai-viet/cong-an-tp-ha-noi-huong-dan-thu-tuc-de-nghi-huy-xac-lap-lai-so-dinh-danh-ca-nhan-khi-cong-dan-bi-sai-cau-truc-so-d131-t35016)
- Chưa chuyển sang M1–M4 hoặc L1–L4. Giữ nguyên test gốc. Cần chủ dự án chốt cách đánh giá số điện thoại giả lập sai cấu trúc nếu điều kiện chuyển pha tiếp tục yêu cầu PHONE trên test gốc phải khác 0. Phép chấm strict và chính sách kiểm số hiện tại được công bố riêng để có thể phân biệt lý do.
