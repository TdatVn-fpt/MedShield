# Phase E — Đăng ký trước phép đo độc lập

Bản đăng ký v1 ngày 25/11/2026, trước mọi chọn mô hình Phase M. Hồ sơ tiếp nhận sẵn sàng để review. Phase E còn chờ phê duyệt nguồn độc lập, người gán nhãn và người phân xử thực tế. Chưa có kết quả IAA hay điểm Phase E. [Thẩm định nguồn ứng viên](phase-e-sources.md)

## E1. Nguồn, tách tập và khai báo lát cắt

- Chọn một trong hai nguồn có phê duyệt của chủ dự án. Một nhóm độc lập với nhóm viết rules có thể xây quy trình sinh và họ mẫu riêng, không xem biểu thức rules, ví dụ lỗi hay dữ liệu Phase Q. Phương án còn lại dùng ghi chú thật đã thay mọi định danh bằng surrogate trong hạ tầng được duyệt. Hồ sơ nguồn lưu phương pháp, phạm vi phép sử dụng, người chịu trách nhiệm và bằng chứng tách khỏi đơn vị phát triển. Không sử dụng tập do agent của dự án sinh để xác nhận chất lượng. Với i2b2, chỉ dùng DBMI Data Portal sau khi chủ dự án tự ký DUA.
- Trước khi gán nhãn và mở dự đoán, định danh bệnh nhân và họ mẫu bằng mã vô danh ổn định. Cả biến thể, ghi chú cùng người bệnh lẫn ghi chú cùng họ mẫu đi vào cùng một split. Test khóa cần ít nhất 150 ghi chú, 800 vùng vàng và đủ năm nhãn; mục tiêu lấy mẫu là 800–1.000 vùng. Validation dùng cho hiệu chuẩn cần ít nhất 100 vùng mỗi nhãn, từ ít nhất 3 họ mẫu mỗi nhãn. Giữ note âm và phổ văn bản giống bối cảnh sử dụng dự kiến.
- Tiểu tập áp lực được người phụ trách nguồn xác định trước, gồm số ngoài cấu trúc `phone_outside_plan`, câu đính chính ngày sinh `dob_correction`, tên viết thường `name_lowercase`, địa chỉ giao hàng `addr_delivery` và văn bản mất dấu `unaccented_text`. Ghi số ghi chú và vùng vàng theo lát, kể cả lát ít mẫu, trước khi đánh giá. Một ghi chú có thể thuộc nhiều lát. Với PHONE, báo riêng các vùng đúng và ngoài cấu trúc theo metadata của thư viện kiểm số đã khóa. Với ADDR, báo riêng có và không có neo cư trú. So sánh trước/sau dùng các lát cố định.

Trước khi phát gói gán nhãn, QA kiểm tách nguồn bằng cùng quy tắc nhóm với bước khóa. Ghi kết quả và ba SHA-256 vào hồ sơ QA. Dùng đúng byte của nguồn test này trong bước chia gói.

```powershell
$private = 'artifacts/local/phase-e-private'
uv run --locked python -X utf8 -m ml.phase_e_preflight "$private/train-groups.jsonl" "$private/validation-source.jsonl" "$private/source.jsonl"
```

`validation-source.jsonl` và `source.jsonl` dùng định dạng chưa gán mô tả bên dưới. Công cụ từ chối khi trùng bệnh nhân hoặc họ mẫu giữa các split, trùng văn bản hoặc mã giữa validation và test, hoặc khi nguồn chưa đủ số ghi chú, họ mẫu và lát đã khai báo. Đầu ra chỉ có số đếm và hash. Bước này xác nhận điều kiện của nguồn trước gán. Số vùng vàng, support từng nhãn và IAA được kiểm sau khi có nhãn.

## E2. Gán nhãn và phân xử

1. Hai người gán đọc [hướng dẫn gán nhãn](annotation-guide.md), dùng biên Unicode code point `[start,end)` trên đúng văn bản nguồn được cấp phép. Chạy pilot bằng ghi chú ngoài test và rà lại các bất đồng trước khi khóa. Không dùng ca của test khóa làm ví dụ hướng dẫn hay fixture.
2. Chọn trước tối thiểu 20% ghi chú test để hai người gán độc lập, phân tầng theo nguồn và lát áp lực, lưu seed và danh sách mã đã chọn trong biên lưu trữ được duyệt. Hai người gán không xem dự đoán mô hình hay nhãn của nhau. Ghi riêng người gán thực tế, vai trò và phiên bản guideline. Ghi số ghi chú chủ dự án tự rà soát theo thực tế nếu có.
3. Trước khi phân xử, tính strict micro-F1 của hai lượt gán bằng tuple `(start, end, label)` trên từng ghi chú, cộng TP/FP/FN trên cả mẫu gán đôi. Giữ thêm số liệu theo nhãn. IAA cần ≥ 0,85. Nếu thấp hơn, phân tích biên, sửa hướng dẫn và gán lại pilot; nếu vẫn thấp sau hai vòng thì báo và chờ quyết định. Người thứ ba phân xử mọi bất đồng, lưu quyết định và lý do về biên hoặc nhãn.

### Chia gói gán nhãn và nhận kết quả trên máy nội bộ

QA chuẩn bị `source.jsonl` từ nguồn đã được chủ dự án duyệt. Mỗi dòng có đúng `note_id`, `text`, `family_id`, `patient_group`, `source_group` và `slices`. Giữ nguyên văn bản, dùng mã vô danh, và khai báo nhóm nguồn cùng lát trước khi xem nhãn. Chốt seed và giữ hash của manifest mẫu trong hồ sơ QA. Công cụ vừa bảo đảm tỷ lệ gán đôi tối thiểu 20%, vừa lấy ít nhất một ghi chú từ mỗi nhóm nguồn và lát có mặt. Mỗi người chỉ nhận tệp của mình qua quyền truy cập do QA quản lý: A nhận toàn tập, B nhận mẫu gán đôi. Các gói chỉ có mã ghi chú và văn bản, không kèm dự đoán, lát, dữ liệu nhóm hay nhãn từ lượt kia.

```powershell
$private = 'artifacts/local/phase-e-private'
uv run --locked python -X utf8 -m ml.phase_e_annotation prepare "$private/source.jsonl" "$private/packets" --seed 20261125
uv run --locked python -X utf8 -m ml.phase_e_annotation reconcile "$private/source.jsonl" "$private/packets/packet-manifest.json" "$private/a-return.jsonl" "$private/b-return.jsonl" "$private/reconciled"
uv run --locked python -X utf8 -m ml.phase_e_annotation finalize "$private/reconciled" "$private/adjudication.jsonl" "$private/test.jsonl"
```

QA ghi seed đã chốt vào lệnh `prepare`. Hai tệp trả về và tệp phân xử có mỗi dòng `note_id` và `entities`, kể cả ghi chú không có vùng. Gán trên đúng văn bản của gói và giữ offset Unicode code point. `reconcile` kiểm hash nguồn, tái tạo danh sách gán đôi, kiểm đủ bản ghi và báo IAA strict trước phân xử. Nếu IAA dưới 0,85, làm theo quy trình pilot ở trên. QA chỉ mở `adjudication-input.jsonl` cho người phân xử; tệp này chứa văn bản và hai phương án cho các ghi chú bất đồng. `finalize` áp dụng đúng các quyết định trả về cho ghi chú bất đồng để tạo `test.jsonl`. Giữ riêng `annotations-a.jsonl` và `annotations-b.jsonl` từ bước reconcile để verifier tính lại IAA trước khi khóa. Toàn bộ đầu vào và gói kết quả được giữ trong khu vực lưu trữ đã duyệt.

Người gán có thể mở [trang gán nhãn cục bộ](../scripts/phase-e-label/index.html) trực tiếp bằng Chromium trong môi trường đã duyệt. Mở tệp gán mù của mình, chọn đoạn văn bản, chọn nhãn rồi bấm **Thêm vùng đã chọn**. Khi đã đọc xong, tích **Đã rà soát ghi chú này**, kể cả ghi chú âm. Chỉnh vùng làm mất xác nhận. Trang chuyển selection của trình duyệt sang offset code point của gốc và giữ đúng CRLF, emoji và dấu tổ hợp. **Lưu tiến độ** tạo tệp cục bộ gắn SHA-256 của gói. Khi làm tiếp, mở lại gói đúng byte rồi khôi phục tiến độ. **Xuất nhãn trả QA** phát JSONL đúng định dạng cho `reconcile` sau khi xác nhận đủ mọi ghi chú. Không cần chạy API hoặc kết nối mạng. Giữ gói, tệp tiến độ và tệp nhãn trong biên truy cập của người gán.

Trước khi phát gói, QA ghi SHA-256 của `packets/packet-manifest.json` vào sổ có kiểm soát. Khi chuẩn bị bundle, giữ một bản sao đúng byte của manifest ở cấp gốc và điền hash đã ghi vào trường `packet_manifest_sha256` của provenance. Giữ `source.jsonl` đúng byte. Bộ khóa sẽ tái tạo danh sách mẫu và kiểm rằng hai lượt gán trả đúng tập mã đó. Nội dung văn bản, nhóm bệnh nhân, họ mẫu và lát của bản vàng phải khớp nguồn trước gán. Người kiểm tra đối chiếu thời điểm ghi nhận bằng chứng QA.

Trước lần khóa đầu tiên, sao chép nguyên byte hai lượt gán đã chuẩn hóa từ `reconciled/` và manifest từ `packets/` vào thư mục bundle. Nếu đích đã có, QA đối chiếu SHA-256 với bản đã ghi trước khi tiếp tục.

```powershell
foreach ($entry in 'packets/packet-manifest.json', 'reconciled/annotations-a.jsonl', 'reconciled/annotations-b.jsonl') {
    $target = Join-Path $private (Split-Path $entry -Leaf)
    if (Test-Path -LiteralPath $target) { throw "Tệp bundle đã tồn tại: $target" }
    Copy-Item -LiteralPath (Join-Path $private $entry) -Destination $target
}
```

## E3. Khóa, quyền truy cập và lệnh kiểm chứng

QA giữ bản test, các lượt gán và bằng chứng nguồn riêng. Người chọn mô hình chỉ đọc dữ liệu huấn luyện và validation. Dữ liệu thật, văn bản surrogate chưa được cấp phép chia sẻ, chữ ký và hồ sơ phê duyệt ở trong biên triển khai đã duyệt. Tệp bên dưới là đầu vào cục bộ của công cụ, không commit lên Git. Bản công khai chỉ chứa chỉ số tổng hợp, revision và SHA-256 được phép công bố.

| Tệp | Nội dung cần có |
|---|---|
| `provenance.json` | `schema_version: 1`; `source_type` là `independent_generator` hoặc `approved_surrogate`; `source_evidence_sha256` và `owner_approval_sha256` là hash tài liệu bằng chứng; `independent_of_detection` và `human_blind_double_annotation` là `true`; `annotator_a`, `annotator_b`, `adjudicator` là ba mã vai trò riêng; `participant_reviewed_count` là số ghi chú test do chủ dự án thực sự rà soát. Reviewer đối chiếu người và tài liệu bên ngoài bằng mã, vì công cụ chỉ xác nhận cấu trúc và byte. |
| `source.jsonl`, `packet-manifest.json` | Nguồn chưa gán và manifest chọn mẫu gán đôi, lưu đúng byte trước khi phát gói. `provenance.json` phải có thêm `packet_manifest_sha256`. |
| `train-groups.jsonl` | Một bản ghi cho mỗi cặp `patient_group` và `family_id` có trong bất kỳ tập train nào sẽ được dùng, kể cả khi tăng cường bằng thay thế thực thể. |
| `validation.jsonl`, `test.jsonl` | Mỗi dòng có `note_id`, `family_id`, `patient_group`, `text`, `entities` (danh sách `start`, `end`, `label`) và `slices` (danh sách khóa lát cắt, có thể rỗng). |
| `annotations-a.jsonl`, `annotations-b.jsonl` | Mỗi dòng ghi `note_id` và `entities` của một lượt gán. Hai tệp có cùng nhóm ghi chú gán đôi. Có thể ghi `entities: []` cho ghi chú âm. |
| `adjudication.jsonl` | Dùng cùng định dạng gán, gồm đúng các ghi chú bất đồng và kết quả đã phân xử. Lý do và mã người phân xử lưu riêng trong hồ sơ QA. Có thể là tệp rỗng khi không có bất đồng. |

JSONL dùng UTF-8 không BOM, phân cách dòng bằng LF và có LF cuối. Các mã dùng ký tự ASCII gồm chữ, số, dấu `-` hoặc `_` và không chứa tên người hay mã bệnh án. Từ checkout đã xác minh, dùng đường dẫn riêng do QA quản lý. Ví dụ cho workspace đã được duyệt lưu dữ liệu cục bộ:

```powershell
uv run --locked python -X utf8 -m ml.phase_e_intake check artifacts/local/phase-e-private
uv run --locked python -X utf8 -m ml.phase_e_intake seal artifacts/local/phase-e-private
uv run --locked python -X utf8 -m ml.phase_e_intake verify artifacts/local/phase-e-private
```

`check` chỉ xuất hash và số liệu tổng hợp của bundle. `seal` tạo `phase-e-lock.json` duy nhất, không ghi đè. `verify` chạy lại và đối chiếu tất cả hash, số đếm, thống kê IAA và digest của bản đăng ký. QA xác minh bằng chứng và lưu manifest bằng quyền đọc cố định tại nơi giữ test. CI nội bộ có quyền đọc bundle chạy `verify` trước mọi chấm điểm; CI công khai không nhận dữ liệu hoặc log nội dung. Kiểm tra lại manifest khi đổi tập huấn luyện, quy trình tách hoặc runner. Hồ sơ chỉ ghi E đạt khi reviewer xác minh nguồn, tách nhóm, IAA và chạy lại từ checkout sạch. Mọi bản sửa sau khi khóa phải đăng ký như revision mới, ghi lý do và giữ bản cũ để đối chiếu.

Sau khi đã chọn mô hình bằng validation và chạy suy luận trong biên được duyệt, QA kiểm hash tệp dự đoán và chạy lệnh dưới đây. Tệp dự đoán chỉ lưu mã ghi chú vô danh và vùng máy phát hiện, vẫn thuộc hồ sơ hạn chế truy cập. Artifact chỉ xuất số liệu tổng hợp.

```powershell
$predictionSha = 'THAY_BANG_SHA256_DA_GHI_BOI_QA'
uv run --locked python -X utf8 -m ml.phase_e_evaluate artifacts/local/phase-e-private artifacts/local/phase-e-private/predictions.json --prediction-sha256 $predictionSha --output artifacts/local/phase-e-private/aggregate.json
```

Tệp dự đoán JSON có `schema_version: 1`; `test_sha256`, `manifest_sha256`, `selection_validation_sha256`; `candidate_revision_sha256`, `selection_evidence_sha256`, `inference_evidence_sha256`; `selected_before_test: true` và `observed_inference: true`. Ghi `method` là `rules`, `crf`, `transformer` hoặc `hybrid`, với `mode` tương ứng `rules`, `ner`, `ner` hoặc `hybrid`; `model_checkpoint_sha256` bằng `null` khi dùng rules hoặc là hash checkpoint. `predictions` có đúng một bản ghi `note_id`, `entities: [{start, end, label}]` cho mỗi ghi chú, kể cả ghi chú có danh sách vùng rỗng. Reviewer đối chiếu bằng chứng chọn trước test và nhật ký suy luận, vì hash xác thực byte của tài liệu bằng chứng và không tự xác minh sự kiện đã xảy ra.

## Cổng Phase M đã đăng ký

Mọi cổng áp dụng đồng thời trên tập test độc lập Phase E, trước chỉnh tay. Chọn checkpoint, hiệu chuẩn theo nhãn và chọn ngưỡng trên validation; dùng F2 hoặc sàn recall. Chỉ mở test sau khi đóng băng phương án đã chọn. Một thay đổi sau khi nhìn test yêu cầu đánh giá giữ lại độc lập theo quy trình đã duyệt.

| Chỉ số | Điều kiện |
|---|---:|
| Strict micro-F1 năm nhãn | ≥ 0,88 |
| Strict recall từng nhãn NAME, DOB, ADDR | ≥ 0,90 |
| Strict recall từng nhãn PHONE, ID | ≥ 0,95 |
| Tỉ lệ ghi chú còn sót PHI | ≤ 5% |
| Strict ADDR F1 | ≥ 0,80 |

Tỉ lệ sót PHI là số ghi chú còn ít nhất một code point vàng ngoài khoảng trắng chưa được phủ bởi bất kỳ vùng che nào, chia cho tổng số ghi chú được chấm, kể cả ca âm. Nhãn dự đoán không ảnh hưởng đến phép kiểm độ phủ. Báo riêng số ghi chú có ít nhất một FN strict để phân biệt sai nhãn với phần văn bản còn lộ. Báo strict và partial theo nhãn và micro, TP/FP/FN, số ghi chú sót, CI 95% bằng bootstrap cả ghi chú với ít nhất 1.000 lần lấy mẫu lại, seed và số mẫu, cùng lát đã khai báo. Cổng dùng ước lượng điểm; công bố CI để người đọc đánh giá mức bất định, không thay cổng bằng biên CI. Nếu bất kỳ cổng nào trượt, ghi khoảng cách và lát lỗi rồi trình chủ dự án kế hoạch tiếp theo.

Phase E cần chủ dự án chỉ định nguồn độc lập và nhóm gán nhãn. Nếu chọn nguồn ghi chú thật, cần phê duyệt bằng văn bản, nơi lưu nội bộ và người quản lý quyền truy cập trước khi nhận dữ liệu. Nếu chọn quy trình sinh độc lập, yêu cầu cấp mã revision và ký xác nhận các họ câu không dựa trên rules/test đã có.
