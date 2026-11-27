# Phase Q2 — Chính sách theo ngữ cảnh và kết quả hồi quy

## 1. Việc đã làm

- **Q2.1–Q2.2.** `apps/api/adapters/vi_structured.py` ưu tiên neo liên hệ, DOB và ID. Kiểm tra số, lịch và căn cước thêm bằng chứng cho giá trị có neo. PHONE đứng riêng dùng mức 0,40 cho hình dạng, cộng 0,20 cho độ dài khả dĩ và 0,20 khi khớp vùng đánh số VN. Ứng viên dưới 0,50 lên đầu hàng rà soát theo `source`, vẫn có thể bỏ qua UI. Dãy liên hệ liền nhau được giữ nguyên và máy lẻ có neo là một vùng riêng. DOB hỗ trợ từ dẫn có từ xen kẽ và cặp cũ/mới, phân biệt cụm danh từ như học sinh, từ chối dấu phân tách trộn. [Hướng dẫn biên](annotation-guide.md)
- **Q2.3–Q2.4.** `rules.py` đưa ứng viên chưa xử lý giao nhau vào `apps/api/services/hybrid.py`, rồi giải quyết theo nguồn. CRF được ưu tiên cho NAME/ADDR khi giao nhau, rules có neo được ưu tiên cho DOB/PHONE/ID. Bỏ ngưỡng ADDR 0,75 và bỏ cơ chế ghi đè theo độ bao trọn. `vi_boundaries.py` và `vi_names_places.py` xử lý biên trên nguyên văn và hỗ trợ dấu phân cột/từ dẫn. `ml/tune_hybrid.py` quét F2 chỉ để chẩn đoán: validation hiện có 5–20 vùng/nhãn từ 1–2 họ, dưới mức cần để hiệu chuẩn. Q2 giữ ứng viên của hybrid, chờ đủ dữ liệu để đặt ngưỡng có hiệu chuẩn.
- **Q2.5.** `ml/phase_q2_benchmark.py` dùng scorer strict đã khóa, thêm partial kiểu nervaluate (biên trùng tính 1, giao một phần tính 0,5, ghép 1:1), bootstrap 1.000 lượt theo ghi chú, tỉ lệ ghi chú còn ký tự vàng ngoài vùng che, và kết quả từng lát. Baseline trước Q2 gom dự đoán Phase Q theo offset; hash nguồn và tất cả hàng strict đều đối chiếu với artifact Phase Q. Workflow `.github/workflows/frozen-evaluation.yml` kiểm hash các tập công khai trên CI.

## 2. Số liệu trước và sau

Cột trước là máy Phase Q đã ghi, cột sau là máy Q2. Cùng test và scorer strict. Bootstrap 95% theo ghi chú, báo tất cả CI của strict, partial và leak ở artifact. Không gộp đối chứng tiếng Anh. Test gốc để đối chiếu lịch sử. Tập 150 ghi chú do agent sinh chỉ dùng để kiểm tra hồi quy. Hiện chưa có số trên tập độc lập Phase E. [Artifact đầy đủ](../artifacts/phase-q2-comparison.json)

### Test gốc · 20 ghi chú / 33 vùng vàng

| Chế độ | Micro-F1 strict | Micro-F1 partial | Ghi chú sót PHI | CI 95% strict sau | TP/FP/FN sau |
|---|---:|---:|---:|---:|---:|
| Rules | 40,00% → 74,07% | 44,44% → 74,07% | 65,00% → 40,00% | 54,22%–88,46% | 20/1/13 |
| CRF | 53,33% → 53,33% | 53,33% → 53,33% | 60,00% → 60,00% | 28,55%–72,23% | 12/0/21 |
| Hybrid | 53,06% → 84,75% | 57,14% → 84,75% | 55,00% → 25,00% | 70,18%–94,92% | 25/1/8 |

| Nhãn Hybrid | F1 strict | F1 partial | Recall strict sau | CI 95% strict sau | TP/FP/FN sau |
|---|---:|---:|---:|---:|---:|
| NAME | 75,86% → 82,76% | 79,31% → 82,76% | 70,59% | 60,00%–100,00% | 12/0/5 |
| DOB | 0,00% → 100,00% | 0,00% → 100,00% | 100,00% | 0,00%–100,00% | 4/0/0 |
| PHONE | 0,00% → 88,89% | 0,00% → 88,89% | 100,00% | 50,00%–100,00% | 4/1/0 |
| ID | 33,33% → 57,14% | 33,33% → 57,14% | 40,00% | 0,00%–100,00% | 2/0/3 |
| ADDR | 40,00% → 100,00% | 60,00% → 100,00% | 100,00% | 0,00%–100,00% | 3/0/0 |

Hybrid sau sửa 5/20 ghi chú còn PHI. CI 95% của partial sau là 70,18%–94,92%, của leak là 10,00%–45,00%. Rules và Hybrid đều thu hồi 4/4 DOB và 4/4 PHONE; bốn PHONE vàng nằm ngoài dải hợp lệ. Ba ADDR vàng đều có neo cư trú.

### Test mở rộng để kiểm tra hồi quy · 150 ghi chú / 560 vùng vàng

| Chế độ | Micro-F1 strict | Micro-F1 partial | Ghi chú sót PHI | CI 95% strict sau | TP/FP/FN sau |
|---|---:|---:|---:|---:|---:|
| Rules | 70,69% → 81,00% | 73,92% → 81,00% | 73,33% → 66,67% | 78,13%–83,78% | 388/10/172 |
| CRF | 46,35% → 46,35% | 48,96% → 48,96% | 86,67% → 86,67% | 42,23%–50,40% | 178/30/382 |
| Hybrid | 81,45% → 90,51% | 85,28% → 92,34% | 60,67% → 31,33% | 88,18%–92,71% | 496/40/64 |

| Nhãn Hybrid | F1 strict | F1 partial | Recall strict sau | CI 95% strict sau | TP/FP/FN sau |
|---|---:|---:|---:|---:|---:|
| NAME | 86,08% → 86,08% | 86,08% → 86,08% | 80,00% | 81,21%–90,79% | 136/10/34 |
| DOB | 80,00% → 100,00% | 86,67% → 100,00% | 100,00% | 100,00%–100,00% | 80/0/0 |
| PHONE | 91,67% → 91,67% | 91,67% → 91,67% | 91,67% | 87,93%–94,95% | 110/10/10 |
| ID | 94,74% → 100,00% | 94,74% → 100,00% | 100,00% | 100,00%–100,00% | 100/0/0 |
| ADDR | 40,00% → 77,78% | 60,00% → 88,89% | 77,78% | 68,60%–85,87% | 70/20/20 |

Hybrid còn 47/150 ghi chú có PHI sót. CI 95% của partial sau là 90,40%–94,17%, của leak là 24,00%–38,68%. Hybrid nhận 110/110 PHONE hợp lệ và 0/10 PHONE ngoài dải; DOB đính chính đạt 10/10. Recall ADDR có neo cư trú 75%, không có neo 80%; recall NAME viết thường 26,67%. Chín kiểm tra định lượng hồi quy đều thỏa, gồm phục hồi ADDR về 100% ở test gốc và 77,78% ở test mở rộng. Điều này chỉ xác nhận thay đổi so với mốc hồi quy.

## 3. Phân tích lỗi

Hybrid trên test gốc còn 8 FN không giao vùng và 1 FP không giao vùng. Tập hồi quy có 44 FN không giao vùng và 20 FN lệch biên, 20 FP không giao vùng và 20 FP lệch biên. Các ví dụ bên dưới chỉ dùng để phân tích sau khi đóng băng ứng viên.

| Ca | Ghi chú | Lát | Quan sát |
|---|---|---|---|
| FN | vi-test-005 | ID | Mã người cho mẫu nằm sau cụm mô tả gián tiếp, không có vùng máy đề xuất. |
| FN | vi-test-008 | ID | Mã hồ sơ có tiền tố khác mẫu neo hiện tại. |
| FN | vi-test-017 | NAME viết thường | Tên người thân trong lời trao ca bị bỏ sót. |
| FN | vi-phase-q-051 | ADDR không neo cư trú | CRF chỉ lấy phần giữa, bỏ số nhà và phần quận. |
| FN | vi-phase-q-071 | PHONE ngoài dải | Từ dẫn liên hệ cách xa giá trị, bộ nhận diện bỏ sót số cố định giả lập. |
| FP | vi-test-020 | PHONE đúng dải | Một chuỗi đúng dạng số xuất hiện ngoài mục liên hệ. |
| FP | vi-phase-q-051 | ADDR không neo cư trú | Phần giữa của địa chỉ sai biên, đồng thời sinh FN cho toàn vùng. |
| FP | vi-phase-q-101 | ADDR có neo cư trú | Vùng CRF bắt đầu muộn sau số nhà và loại đường. |
| FP | vi-phase-q-131 | PHONE đúng dải | Mã thiết bị trông như số di động. |
| FP | vi-phase-q-131 | NAME | Một phần tên bệnh viện bị nhận là tên người. |

## 4. Kiểm thử

Từ gốc repo:

```powershell
uv run --locked pytest -q
uv run --locked ruff check apps/api ml tests
uv run --locked ruff format --check apps/api ml tests
uv run --locked mypy apps/api ml tests
uv run --locked python scripts/check_source.py
uv run --locked python -m ml.phase_q2_benchmark --output artifacts/local/q2-recheck.json
```

Kiểm tra Q2 qua 216 test Python. `npm.cmd run lint`, `npm.cmd run typecheck`, `npm.cmd run format:check`, `npm.cmd run build` và `npm.cmd run test:e2e` từ `apps/web/` đều chạy thành công. Chromium 23/23 gồm ca Q2 mới, định tuyến API thật, rà soát rồi xuất, hủy kết quả cũ, PDF có lớp chữ và bố cục 390/1440 px. Tập test và scorer khóa có cùng SHA-256. [Biên bản độc lập](reviews/phase-q2.md) lưu kết quả từ bản source sạch. WebGL fallback chưa thuộc phạm vi Q2.

## 5. Rủi ro và việc chưa làm

Giữ rà soát trước xuất. Tập gốc nhỏ có CI rộng và vẫn lộ vùng ở 5/20 ghi chú. Kết quả của tập hồi quy không chứng minh khả năng tổng quát hay vượt cổng Phase M. Chưa hiệu chuẩn score trên validation độc lập, chưa có dữ liệu và điểm IAA cho Phase E, chưa chọn hoặc huấn luyện transformer phục vụ Phase M. G4 và G5 còn các công việc theo bảng chặng.

## 6. Quyết định cần chủ dự án

Chỉ định nguồn Phase E độc lập, hai người gán nhãn và một người phân xử. Nếu nguồn là ghi chú thật, chốt quyền sử dụng và nơi xử lý nội bộ trước khi nhận dữ liệu. Nếu nguồn là nhóm tổng hợp độc lập, tách người tạo họ câu khỏi nhóm phát triển hiện tại. Cổng M đã đăng ký trước, còn nguyên strict micro-F1 0,88, recall 0,90/0,95, leak 5% và ADDR F1 0,80. [Quy trình Phase E](phase-e.md)
