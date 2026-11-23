# Nhập PDF bệnh án giả lập trên Windows

**PDF-04** · Hướng dẫn cho MedShield có luồng nhập PDF cục bộ.

## Khởi động

Cần `uv`, Node.js 24 và npm. Ví dụ dưới đây dùng checkout `D:\Workspace\MedShield`. Điều chỉnh đường dẫn nếu bạn đặt repo ở nơi khác.

**Cửa sổ 1 · API**

```powershell
Set-Location D:\Workspace\MedShield
uv sync --locked --python 3.11.7
uv run --locked uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

**Cửa sổ 2 · Web**

```powershell
Set-Location D:\Workspace\MedShield\apps\web
npm ci
npm run dev
```

Giữ cả hai cửa sổ mở. Vào [MedShield](http://127.0.0.1:5173/). Nếu gặp lỗi cổng đã được dùng, thử mở web và kiểm tra API trước khi khởi động lại. Nếu web báo chưa kết nối API, mở [trang kiểm tra API](http://127.0.0.1:8000/health) và xem cửa sổ 1. Trước khi demo, kiểm mục `vi/hybrid` có trạng thái `available`.

## Demo ba phút

Chọn [PDF bệnh án ngoại trú mô phỏng](evidence/demo-benh-an-ngoai-tru.pdf). Tệp có hai trang, mỗi trang ghi rõ **DỮ LIỆU GIẢ LẬP**.

| Thời gian | Thao tác |
|---|---|
| 0:00–0:45 | Bấm **Nhập PDF** và chọn tệp mẫu. Đặt **Trang đầu** là `1`, **Trang cuối** là `2`. Bấm **Trích văn bản**. Nếu chọn nhầm tệp, dùng **Hủy nhập PDF** rồi chọn lại. |
| 0:45–1:20 | Trong **Văn bản gốc**, so dấu tiếng Việt, số, thứ tự dòng và ngày tái khám với PDF. Sửa văn bản nếu cần trước khi chọn **Tiếng Việt**, **Kết hợp · hybrid** và bấm **Phân tích**. |
| 1:20–2:25 | Rà soát năm vùng AI đề xuất. Với mẫu đã kiểm tra, `tạ hư cấu` còn nguyên. Bôi chọn tên, chọn `NAME` rồi bấm **Thêm vùng che**. Kiểm **Bản đã che**, chọn **Tôi đã rà soát toàn bộ nội dung** rồi bấm **Tải TXT**. |
| 2:25–3:00 | Mở TXT đã tải, đối chiếu với bản xem trước. Chỉ ra ký hiệu thay tên đã duyệt và ngày tái khám `18/12` còn nguyên. |

## Phạm vi và bằng chứng

- **Cần PDF có lớp chữ.** Trình duyệt trích chữ tại chỗ. Khi bấm **Phân tích**, API nhận văn bản. Bản này không có OCR. Nếu trang là ảnh scan, chọn lại dải trang có chữ hoặc chuẩn bị TXT UTF-8.
- **Xuất TXT hoặc JSON sau rà soát.** Bản này không xuất PDF đã che giữ bố cục.
- **Giới hạn:** 10 MiB mỗi tệp, tối đa 10 trang mỗi lần trích và 50.000 Unicode code point. Luôn đối chiếu thứ tự các trường với PDF gốc, nhất là biểu mẫu nhiều cột.
- **Kiểm thử:** Từ `apps/web`, chạy `npm run test:e2e -- pdf-import.spec.ts`. Lần đầu, nếu chưa có Chromium của Playwright, chạy `npx playwright install chromium`.

[Kế hoạch nhập PDF](plan-nhap-pdf-benh-an.md) · [Môi trường Windows](environment.md)

Bản xuất từ ca demo để đối chiếu: [TXT đã rà soát](evidence/demo-benh-an-ngoai-tru.reviewed.txt) · [JSON đã rà soát](evidence/demo-benh-an-ngoai-tru.reviewed.json).
