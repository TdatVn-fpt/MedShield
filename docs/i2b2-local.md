# Bộ đọc cục bộ i2b2 2014

Bộ đọc chuẩn bị cho đối chứng tiếng Anh riêng. Nguồn chính thức do Harvard DBMI quản lý và yêu cầu quyền truy cập cá nhân theo DUA. Chủ dự án tự làm thủ tục nếu quyết định dùng. Không tải từ mirror hoặc chia sẻ bản sao cho người chưa được cấp quyền. [Điều kiện truy cập và danh mục chính thức](https://n2c2.dbmi.hms.harvard.edu/data-sets)

`ml/i2b2_reader.py` đọc XML stand-off của Track 1 từ một tệp, thư mục XML hoặc archive `tar.gz` được cung cấp cục bộ. Bộ đọc nhận `TEXT` và `TAGS`, kiểm tra khoảng nửa mở đối chiếu với chuỗi trong thẻ, giữ cả nhóm và loại gốc. `DATE` của i2b2 bao gồm các ngày ngoài ngày sinh, nên vẫn giữ `DATE` nguyên dạng và dùng riêng với năm nhãn MedShield. [Phân loại do tác giả corpus công bố](https://pmc.ncbi.nlm.nih.gov/articles/PMC4978170/)

Trong môi trường đã được phép xử lý dữ liệu, từ gốc checkout:

```powershell
$localSource = 'D:\thu-muc-duoc-duyet\file.xml'
uv run --locked python -X utf8 -m ml.i2b2_reader $localSource
```

Lệnh chỉ xuất số tài liệu, số vùng và tổng theo nhóm gốc. Archive được đọc trực tiếp, không giải nén ra đĩa. Khi XML lỗi, biên sai hoặc giá trị thẻ khác đoạn `TEXT`, lệnh dừng với lỗi chung, không in văn bản, mã ghi chú, offset hay đường dẫn nguồn. Nếu XML chuẩn hóa dấu xuống dòng và offset không còn khớp, báo lỗi để người phụ trách kiểm tra bản phát hành.

Đã kiểm thử bằng XML tự tạo với emoji, dấu tổ hợp, nhãn ngày khám, biên sai và archive cục bộ. Chưa chạy trên corpus DBMI, chưa có dữ liệu hay chỉ số i2b2 trong repo. Công cụ này không thay thế tập tiếng Việt độc lập Phase E.
