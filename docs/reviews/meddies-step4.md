# Review kỹ thuật độc lập Meddies · Bước 4

Ngày 26/11/2026. **PASS cho bốn kiểm soát truy vết mã nguồn đã review**, sau khi sửa các điểm của lượt **CHANGES_REQUESTED**. Bước 4 vẫn đang thực hiện. IAA, kết quả gán và khóa tập silver thực tế vẫn đang chờ.

## Phạm vi và lệnh

Kiểm `ml/meddies_silver.py`, `ml/meddies_lock.py`, `ml/meddies_slices.py` và `tests/test_meddies_silver.py`, cùng các nơi tạo manifest đầu vào. Thư mục bằng chứng thực được kiểm tra tên tệp, không mở văn bản trong gói mù hoặc nhãn. Không chạy lệnh khóa trên dữ liệu thật.

```powershell
uv run --locked pytest -q tests/test_meddies_silver.py tests/test_meddies_intake.py tests/test_meddies_dedup.py tests/test_meddies_split.py tests/test_phase_e_intake.py tests/test_phase_e_evaluate.py
uv run --locked ruff check ml/meddies_silver.py ml/meddies_lock.py ml/meddies_slices.py tests/test_meddies_silver.py
uv run --locked ruff format --check ml/meddies_silver.py ml/meddies_lock.py ml/meddies_slices.py tests/test_meddies_silver.py
uv run --locked mypy ml/meddies_silver.py ml/meddies_lock.py ml/meddies_slices.py tests/test_meddies_silver.py
uv run --locked python scripts/check_source.py
```

36/36 test qua, Ruff và mypy qua, kiểm mã nguồn không thấy vi phạm. Probe CLI có một ca seal/verify thành công trên fixture, tái seal bị từ chối, thiếu đầu vào bị từ chối và không viết lockfile. Ca có hai lượt gán khác nhau dùng scorer strict trước phân xử. Full seal từ chối ngay khi IAA dưới 0,85 dù kết quả phân xử từng được chấp nhận cho bộ nhãn khác. Tệp sau phân xử phải khớp quyết định của chủ dự án. Các mức support và cổng Phase M đang được giữ nguyên.

## Điểm cần bổ sung

1. `request-manifest.json` mô tả lời gọi Qwen và có trước kết quả; chưa ràng buộc SHA-256 của `annotations-b.jsonl`. Probe đổi riêng nội dung B giữ nguyên receipt và thấy `inspect` vẫn chấp nhận, IAA thay đổi. Verify sau khi khóa phát hiện thay đổi, nhưng lượt khóa đầu có thể nhận nhầm tệp. Nên ràng buộc biên nhận hoàn tất với digest, số dòng, model, prompt, runtime, guideline và gói.
2. `inspect` tin hash gói do tệp manifest nguồn được truyền vào khai báo. Giữ đúng revision và hash shard trong một fixture tự dựng rồi cấp hash gói khác vẫn có thể tạo lock; cùng một văn bản ở hai split không được phát hiện nếu tệp manifest tự dựng bảo chứng. Cần ghim hash của manifest Bước 3 đã được QA xác nhận, hoặc tái kiểm bao phủ và cô lập nguồn từ bằng chứng có hash ghim.
3. Phiếu rà ánh xạ ràng buộc 100 quyết định với byte mẫu hiện hành, nhưng manifest Bước 2 không có SHA-256 tệp mẫu và khóa chưa kiểm tệp mẫu phát sinh từ đúng tập train đã duyệt. Hash tệp mẫu cần gắn cùng digest tập train ở Bước 2/Bước 3.
4. `slice_protocol_sha256` bảo vệ `meddies_slices.py`, còn định nghĩa trong `evaluation_slices.py` mà code nhập có thể thay đổi phân lát mà không đổi digest đó. Nên đóng băng các module tham gia hoặc một đặc tả cấu hình đóng gói đủ phụ thuộc.

Tiếp tục lưu kết quả thuật toán và fixture tách khỏi bằng chứng thật. Thư mục Bước 4 lúc kiểm tra chỉ có phiếu rà ánh xạ, chưa thấy gói nhãn trả, phân xử và manifest khóa đã hoàn tất. IAA người–LLM và support thực tế vẫn là điều kiện phải đo trước khi khóa; việc có công cụ hoặc test xanh không làm các cổng dữ liệu đạt.

## Kiểm tra lại sau sửa

- SHA-256 thô của manifest Bước 3 công khai khớp hằng số ghim; scorer khớp SHA-256 đóng băng. Probe gọi `inspect` bằng manifest tự dựng và thay đúng một byte của bản đã ghim trong fixture. Cả hai bị từ chối.
- Fixture đủ support và có biên nhận hoàn thành được chấp nhận. Thay riêng một byte của tệp nhãn B, một byte của manifest yêu cầu, hoặc số dòng ghi ở biên nhận làm lệnh kiểm tra từ chối trước lần khóa đầu. Biên nhận ràng buộc tính toàn vẹn của tệp; việc Qwen thực sự đã chạy được xác minh riêng bằng bằng chứng thực thi.
- Hai báo cáo tổng hợp Bước 2 và 3 khớp SHA-256 tập train đã ánh xạ. Báo cáo mapper có SHA-256 bộ mẫu; thay mẫu và cập nhật phiếu soát theo mẫu thay thế bị từ chối. Đổi riêng SHA-256 tập train trong báo cáo mapper cũng bị từ chối. Lượt đầu tái hiện trường hợp sửa đồng thời báo cáo mapper, mẫu và phiếu soát. Sau khi ghim SHA-256 thô của báo cáo mapper, probe mới xác nhận thay đồng thời báo cáo và mẫu bị từ chối trước khi xác minh phiếu. Hai báo cáo tổng hợp hiện có đều khớp hằng số ghim.
- Thay từng tệp trong `ml/meddies_slices.py`, `ml/evaluation_slices.py` và `uv.lock` trong fixture làm payload khóa thay đổi. Trả lại đúng byte khôi phục đúng payload. IAA validation vẫn được báo riêng, cổng 0,85 áp dụng ngay khi kiểm tra test trước phân xử.

Lượt kiểm tra lại chạy 36/36 test liên quan, Ruff, kiểm định dạng, mypy và kiểm quy tắc mã nguồn đều qua. Probe dùng thư mục tạm riêng và ghi chú giả lập. Không mở gói mù, nhãn hoặc bề mặt mẫu thực tế.
