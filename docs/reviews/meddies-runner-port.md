# Review độc lập bảo vệ cổng lượt gán B

Ngày 27/11/2026. Tác giả thay đổi là agent DevOps `/root/devops`. Reviewer là agent QA `/root/qa`. Phạm vi E1–E3, cơ chế giành cổng, kiểm chủ sở hữu và giữ các giá trị ghim của `scripts/run-meddies-annotator.ps1`. SHA-256 của bản được kiểm là `b1fe2fbe639ffc74885fe8305d812bd792ddfa126b3c4314b661a484bbecd0c8`.

| Tiêu chí | Thao tác và kết quả QA |
|---|---|
| Cú pháp | `System.Management.Automation.Language.Parser.ParseFile` trả 0 lỗi với Windows PowerShell 5.1.26100.9818. |
| Cổng 18240 đã có lượt B | `Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 18240 -State Listen` xác nhận một listener, PID 12856. Gọi runner thật với `-Split test`, có hàm chặn các bước kiểm tệp, khởi chạy và gửi HTTP, trả `The Meddies local port is already occupied.`. Đo lại cùng cổng vẫn là PID 12856. |
| Cạnh tranh khóa | Giữ mutex `Global\MedShield.Meddies.Annotator.18240` rồi chạy runner trong runspace riêng. Runner trả `Another Meddies annotation process already holds the local port lock.` trước truy vấn cổng. QA giải phóng khóa sau phép thử. |
| Lỗi đọc bảng TCP | Truy vấn một cổng tạm đã đóng trả `CmdletizationQuery_NotFound,Get-NetTCPConnection`, khớp nhánh hiểu là cổng trống. Mô phỏng lỗi truy vấn khác qua `Get-MeddiesListener` cho thấy lỗi được truyền ra để dừng. |
| Chủ sở hữu listener | Gọi hàm `Assert-MeddiesListener` lấy từ AST với fixture. Hàm chấp nhận duy nhất listener ở `127.0.0.1` với PID kỳ vọng. Hàm từ chối thiếu listener, sai PID, địa chỉ `0.0.0.0` và trường hợp có hai listener. |
| Ghim mô hình và runtime | Hai SHA-256 GGUF và llama.cpp `b12754` khớp khai báo trong repo. Runner vẫn kiểm từng shard, kiểm chuỗi build `12754, commit 244640b7f`, đặt alias Qwen đã đăng ký và bind `127.0.0.1`. Ca mô phỏng checksum shard sai trả `Shard Qwen does not match the registered SHA-256.` trước khi chạy executable. [Khai báo nguồn](../../THIRD_PARTY.md) |

## Lệnh và phạm vi kiểm

Các phép kiểm PowerShell dùng `Get-FileHash -LiteralPath 'scripts/run-meddies-annotator.ps1'`, `Parser.ParseFile`, `Get-NetTCPConnection` và `& $qaRunner -Split test` trong scope có hàm chặn khởi chạy. Ca cạnh tranh dùng `[runspacefactory]::CreateRunspace()` trên luồng riêng. Các tình huống chủ sở hữu dùng fixture thay cho bảng TCP. Kiểm cuối xác nhận listener ban đầu còn ở PID 12856. Các phép thử dừng trước khi mở gói gán hoặc ghi checkpoint.

Runner giữ mutex từ trước lúc kiểm cổng đến phần dọn và dừng tiến trình qua đối tượng mà chính lượt đó đã khởi tạo. Quyền sở hữu listener được kiểm sau khi runtime báo sẵn sàng và trước mỗi split. Trong một split, vòng lặp Python gửi request sau phép kiểm này. Bằng chứng hiện có xác nhận chặn các lượt cạnh tranh qua runner cùng khóa và từ chối listener sai chủ tại các mốc kiểm.

**PASS phạm vi kỹ thuật bảo vệ cổng khi khởi chạy.** Review xác nhận các nhánh từ chối và giá trị ghim trên bản SHA nêu trên. Lượt B đang dùng tiến trình đã chạy trước khi sửa runner. Kết quả gán B và khóa silver được kiểm riêng.
