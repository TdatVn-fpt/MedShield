# Meddies-first — Giao thức silver-locked, 26/11/2026

## 1. Phân tập và khử trùng

Chủ dự án duyệt giao thức thay sổ nhóm. Giữ shard Meddies tiếng Việt tại revision `5dbe7cde649446028f628820c204bf53bb296894` (CC BY-NC 4.0). Toàn bộ 22.310 ghi chú train tạm đến từ 13 giá trị `source` khác với nguồn lâm sàng giữ riêng cho đánh giá. Checksum shard và danh mục nguồn nằm trong [manifest khử trùng](../artifacts/meddies-step3-dedup.json).

- Tính Jaccard chính xác trên tập word 5-gram, NFC và casefold, giữ dấu tiếng Việt. So 299 ứng viên với cả 22.310 ghi chú train tạm, tổng cộng 6.670.690 cặp. Loại khi điểm cao nhất **> 0,5**. Có 53 ứng viên đạt tối đa 0, 246 nằm trong khoảng (0; 0,1], p50 0,00469, p95 0,01493 và cực đại 0,03077. Không có ứng viên vượt ngưỡng.
- So tên đi cùng số điện thoại hoặc ngày sinh đầy đủ trong nhãn **train** đã ánh xạ, dò tổ hợp trong nguyên văn ứng viên. Chuẩn hóa cách viết ngày phổ biến, dấu phân tách và tiền tố +84 của số. Không phát hiện tổ hợp trùng. Phép dò dùng bề mặt train đã ánh xạ, nên phụ thuộc độ phủ nhãn nguồn, không suy ra bệnh nhân hoặc các biến thể tên khác dấu.
- Còn 299 ứng viên. Chia theo loại tài liệu với seed 20261126, giữ 150 test và 149 validation để tập validation có nhiều ghi chú nhất trong phạm vi test đã đăng ký. Jaccard lớn nhất qua biên validation/test là 0,10527. Quy mô mỗi nhãn được kiểm sau gán.
- Độ dài: p50 ứng viên 362 code point, p95 420, trong khi train p50 1.156, p95 2.283. Có 16 loại tài liệu trong đánh giá. Phân bố đầy đủ theo tập trong manifest. Các ghi chú ngắn hơn đáng kể nên phép đo có giới hạn khi suy rộng sang ghi chú dài.
- Giới hạn áp dụng cho manifest và mọi lần công bố: “tách tập bằng cô lập nguồn sinh + khử trùng trùng lặp gần giống; phân nhóm bệnh nhân/họ mẫu không kiểm chứng được từ metadata công khai của nhà phát hành”.

```powershell
$d = 'artifacts/local/meddies'
uv run --locked --with pyarrow==20.0.0 python -X utf8 -m ml.meddies_dedup "$d/vietnamese.parquet" "$d/step2-reviewed/provisional-train.jsonl" "$d/step3-recheck" "$d/step3-recheck.json"
```

Đầu ra mới dùng đường dẫn chưa tồn tại. Gói gán chỉ gồm mã và văn bản nguyên gốc. Hai lượt chạy phải cho cùng SHA-256 từng gói. Scorer `ml/scoring.py` có SHA-256 `6f3f4e8b4c242c6f418003cb192a1dba967ad3161b0957a89adc9c3e5ab512c0`. Test lịch sử `data/test.jsonl` giữ SHA-256 `ad2dce2254e1eac809df51f5a827f64bfdb425babf1ca56cb5db87f7dea9bb96`.

## 2. Việc chủ dự án thực hiện

1. Đọc [hướng dẫn gán nhãn](annotation-guide.md) và mở [trang gán offline](../scripts/phase-e-label/index.html) bằng Chromium. Lần lượt nạp `validation-blind.jsonl` và `test-blind.jsonl` trong `artifacts/local/meddies/step3-source-isolated/`. Đánh dấu tất cả ghi chú đã rà soát, kể cả ghi chú không có thực thể. Mỗi gói có chức năng **Lưu tiến độ** và **Khôi phục tiến độ**. Sau khi hoàn thành, lưu hai tệp **Xuất nhãn trả QA** thành `validation-a.jsonl` và `test-a.jsonl` trong `artifacts/local/meddies/step4/`.
2. Rà 100 mẫu ở `artifacts/local/meddies/step2-reviewed/train-mapping-samples.json`. Mỗi nhãn có đúng 20 mẫu đánh số theo thứ tự trong mảng tương ứng, bắt đầu từ 1. Ghi `ok` hoặc `needs_correction` và lý do cho từng dòng trong mẫu `artifacts/local/meddies/step4/mapping-review.csv`. Nêu rõ nếu sai nhãn, sai biên hoặc không phải định danh. Kết quả dùng để quyết định phần ánh xạ train có cần sửa trước huấn luyện.
3. Khi cả A và B hoàn thành, công cụ công bố IAA strict người–LLM trước bất kỳ phân xử. Nếu IAA test dưới 0,85, làm theo vòng chỉnh guideline và gán lại đã duyệt. IAA validation được báo riêng. Chủ dự án phân xử mọi ghi chú bất đồng và ghi lý do, dùng đúng văn bản và offset Unicode code point. Chỉ sau đó mới được tính support để khóa.

### Kiểm tệp A đã nhận

Ngày 27/11/2026, dùng `packet_rows` và `parse_returns` từ `ml.meddies_silver` qua `uv run --locked python -X utf8 -` để đối chiếu các tệp A của chủ dự án với đúng gói mù. Hash gói mù khớp manifest Bước 3. Mỗi mã xuất hiện đúng một lần, vùng dùng biên Unicode code point hợp lệ và không chồng lấn. Hai tệp A giữ nguyên byte trong `artifacts/local/meddies/step4/`.

| Tập | Ghi chú | Tổng vùng | NAME | DOB | PHONE | ID | ADDR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Validation | 149 | 863 | 288 | 139 | 149 | 149 | 138 |
| Test | 150 | 864 | 289 | 139 | 150 | 150 | 136 |

- `validation-a.jsonl`: SHA-256 `611aad0b49649fc440ae6ec7745827cd7eb3c02d3bfa12167aa435ff1d8189da`.
- `test-a.jsonl`: SHA-256 `6cc9fe43a5fa8d2fd1c3560d9cc3b9440ae0a6187a1e913d2dc423d1cb6d1cfd`.

Tổng và số vùng từng nhãn khớp đủ mốc bàn giao. Đây là số đếm toàn bộ lượt A trên benchmark synthetic độc lập, học thuật. Support dùng để khóa sẽ được tính lại trên kết quả sau phân xử.

## 3. Lượt gán LLM độc lập

Sử dụng Qwen2.5-7B-Instruct Q4_K_M cục bộ. Mỗi yêu cầu chỉ chứa một ghi chú, [hướng dẫn gán nhãn](annotation-guide.md) và chỉ dẫn định dạng. Không gửi nhãn nhà phát hành, nhãn người gán hoặc dự đoán rules. Chạy trên cả hai gói nên mức gán đôi dự kiến là 100%. Đo IAA trên test và validation riêng. Mô hình và runtime xem [THIRD_PARTY.md](../THIRD_PARTY.md).

Đã kiểm SHA-256 của cả hai shard GGUF và chạy thử trên CPU Windows. Fixture riêng có hai vùng NAME/DOB, Qwen trả cả hai với biên code point khớp nguyên văn. Biên nhận hoàn tất ràng buộc nhãn B với yêu cầu, số ghi chú và SHA-256 đầu ra. Kết quả fixture chỉ xác nhận đường chạy của lượt gán.

Khi một ghi chú hết số lần thử do lỗi đầu ra, lệnh `ml.meddies_probe` kiểm nhật ký lượt chính rồi gọi lại cùng Qwen trên đúng ghi chú mù với chỉ dẫn về JSON gọn. Giới hạn 256 hoặc 512 token được ghi vào biên nhận. Ghi chú validation số 7 đã qua phép thử 256 token với 5 vùng hợp lệ về định dạng và biên. Kết quả đã được lưu riêng sau khi đối chiếu SHA-256 của gói, guideline, prompt và dòng nhãn. Khi chạy tiếp, runner chỉ dùng kết quả thử lại nếu vị trí đó chưa có checkpoint chính. Manifest hoàn tất ghi biên nhận thử lại và ràng buộc nó với đúng dòng kết quả. Các vùng này vẫn thuộc lượt B và sẽ được tính trong IAA trước khi phân xử.

```powershell
$d = 'artifacts/local/meddies'
uv run --locked python -X utf8 -m ml.meddies_annotator "$d/step3-source-isolated/validation-blind.jsonl" docs/annotation-guide.md "$d/step4/validation-qwen" --stage-recovery "$d/step4/validation-qwen-recovery-probe-0007"
```

Để thử một vị trí chưa có kết quả khi tiến trình cục bộ còn đang nghe, dùng lệnh dưới đây với số thứ tự đã có mục `needs retry` và giới hạn chưa dùng cho ghi chú đó. Lệnh tự lưu riêng và tiếp nhận kết quả nếu đầu ra hợp lệ.

```powershell
$worker = Get-Content -Raw "$d/step4/annotator-process.json" | ConvertFrom-Json
uv run --locked python -X utf8 -m ml.meddies_probe validation 8 $worker.stdout --max-tokens 512
```

Ghi chú validation số 8 cần thêm một lượt thử với ngữ pháp ràng buộc từng cặp `start` và `value`. Ngữ pháp chỉ cho phép các đoạn liên tục khớp nguyên văn tại đúng vị trí code point và giữ cả năm lựa chọn nhãn. Runtime xác nhận ngữ pháp đã áp dụng. Kết quả có 10 vùng hợp lệ, được lưu riêng với SHA-256 prompt, ngữ pháp và dòng nhãn. Trình xác minh tạo lại cả prompt ChatML đã định dạng và ngữ pháp từ đúng ghi chú nguồn. Kết quả sẽ được đối chiếu với nhãn người trong cùng quy trình IAA.

```powershell
uv run --locked python -X utf8 -m ml.meddies_annotator "$d/step3-source-isolated/validation-blind.jsonl" docs/annotation-guide.md "$d/step4/validation-qwen" --stage-recovery "$d/step4/validation-qwen-recovery-source-offset-0008"
```

Với vị trí khác đã có lỗi và chưa có kết quả, dùng lệnh probe ở trên với `--source-offset`. Lệnh đối chiếu prompt đã định dạng từ `/apply-template` và ngữ pháp trả về từ `/completion` của runtime cục bộ trước khi chấp nhận nhãn. [Giao diện llama.cpp b12754](https://github.com/ggml-org/llama.cpp/blob/b12754/tools/server/README.md#post-apply-template-apply-chat-template-to-a-conversation)

```powershell
powershell.exe -NoProfile -File scripts/run-meddies-annotator.ps1 -Smoke
powershell.exe -NoProfile -File scripts/run-meddies-annotator.ps1
uv run --locked python -X utf8 -m ml.meddies_silver "$d/step3-source-isolated" "$d/step4" artifacts/meddies-step3-dedup.json "$d/step4-pre-adjudication" --mapping-samples "$d/step2-reviewed/train-mapping-samples.json" --mapping-review "$d/step4/mapping-review.csv"
```

Runner cho lần khởi chạy mới giữ mutex theo cổng 18240 và kiểm listener thuộc tiến trình nó vừa tạo khi runtime sẵn sàng và trước từng split. Phép kiểm độc lập xác nhận lệnh từ chối một lần khởi chạy trùng trong khi lượt B đang chạy. [Biên bản kiểm cổng](reviews/meddies-runner-port.md)

Lệnh cuối xác minh lại phiếu rà nguyên bản, xuất tổng hợp IAA trước phân xử và một tệp bất đồng riêng cho từng split. Bàn giao gói khi lệnh thoát thành công và có `review.json` đủ hai tập. Trong trang gán offline, mở `<split>-adjudication-packet.jsonl` rồi khôi phục bản nháp `<split>-adjudication-draft-a.json` hoặc `<split>-adjudication-draft-b.json` nếu muốn bắt đầu từ một lượt gán. Hai bản nháp đều đặt mọi ghi chú ở trạng thái chưa rà soát. Tệp `<split>-disputes.jsonl` có cả hai phương án để đối chiếu.

Xuất và lưu quyết định ở `step4/validation-adjudication.jsonl` và `step4/test-adjudication.jsonl`. Dùng tệp rỗng khi không có bất đồng. Sau phân xử, chạy lại với thư mục đầu ra mới. Giữ lý do phân xử ở hồ sơ nội bộ.

## 4. Kiểm trước khóa và Phase M

Tập đánh giá ghi `silver-locked`, IAA ghi `human_llm`, vai trò người gán và trọng tài đều là chủ dự án. Manifest khóa phải ghi đúng số ghi chú đã được chủ dự án xem và ghi hash shard, quy tắc nguồn, manifest khử trùng, gói mù, phiên bản guideline, kết quả hai lượt, phân xử, phiếu soát ánh xạ và bản dữ liệu sau phân xử. Test cần đủ 150–200 ghi chú, ít nhất 800 vùng, đủ năm nhãn và IAA strict ≥0,85. Validation cần ít nhất 100 vùng mỗi nhãn. Xác minh họ mẫu đã được thay bằng giao thức khử trùng được duyệt. Không dùng nhãn Meddies gốc làm chuẩn đánh giá.

Đăng ký trước các lát: NAME viết thường nếu vùng vàng có chữ và toàn bộ chữ đều thường; toàn bộ ID; PHONE ngoài cấu trúc theo phiên bản thư viện kiểm số đã khóa, PHONE neo xa khi có từ dẫn cùng dòng cách vùng từ 14 code point trở lên và không có từ dẫn gần hơn; toàn bộ DOB và ca đính chính; ADDR có/không có từ dẫn cư trú cùng dòng trong 48 code point trước vùng; ghi chú tiếng Việt không có dấu. Khoảng cách đo trên code point nguyên văn. Chốt danh sách từ dẫn trong code trước huấn luyện và trước khi đọc dự đoán. Báo support thực tế từng lát, kể cả lát rỗng.

QA lưu bản sau phân xử đã kiểm, các đầu vào đã dùng và xác nhận của chủ dự án trong thư mục bằng chứng cục bộ. `owner-attestation.json` ghi `owner`, `guideline_sha256`, `revision_round` (0–2) và bốn xác nhận thực tế `human_annotation_complete`, `adjudication_complete`, `mapping_review_complete`, `mapping_corrections_resolved`. Lệnh khóa tính lại IAA, phân xử, support và checksum từ các tệp gốc thay vì dùng lại báo cáo xem trước.

```powershell
uv run --locked python -X utf8 -m ml.meddies_lock seal "$d/step3-source-isolated" "$d/step4-verified" artifacts/meddies-step3-dedup.json "$d/step2-reviewed/train-mapping-samples.json" docs/annotation-guide.md
uv run --locked python -X utf8 -m ml.meddies_lock verify "$d/step3-source-isolated" "$d/step4-verified" artifacts/meddies-step3-dedup.json "$d/step2-reviewed/train-mapping-samples.json" docs/annotation-guide.md
```

Cổng Phase M giữ nguyên đồng thời strict micro-F1 ≥0,88, strict recall NAME/DOB/ADDR ≥0,90 và PHONE/ID ≥0,95, tỉ lệ ghi chú còn sót PHI ≤5%, strict ADDR F1 ≥0,80. Báo strict và partial, CI bootstrap 95% theo ghi chú, kết quả theo nhãn và lát, suy luận CPU p50/p95. Chọn mô hình, hiệu chuẩn và chỉnh ngưỡng trên validation. Tập test khóa được mở để chấm sau khi cấu hình đã đóng băng. [Định nghĩa và giao thức chấm Phase E](phase-e.md)
