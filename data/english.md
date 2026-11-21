# Bộ đối chứng tiếng Anh G2

`data/english.jsonl` · revision `en-g2-v1` · **READY_FOR_REVIEW** · BA soạn và gán nhãn, QA kiểm độc lập. Đây là 16 ghi chú giả lập do Codex viết thủ công từ 16 họ tình huống, không dùng hồ sơ thật hay đầu ra engine. Số điện thoại dùng dải ví dụ NANP 555-01xx. Không dùng seed để sinh mẫu. Số mẫu do người học trực tiếp rà soát đã xác nhận là 0.

## Đầu vào dùng chung

Presidio, Philter UCSF và GEMINI pyDeid nhận cùng giá trị `text` đã giải mã JSON của từng `note_id`. Giữ thứ tự ghi chú và ký tự gốc, gồm CRLF trong văn bản, emoji và dấu tổ hợp. Mỗi dòng JSONL có `note_id`, `family_id`, `text`, `entities`. Các span vàng chỉ chứa `start`, `end`, `label` và dùng khoảng Unicode code point `[start,end)` theo [hướng dẫn gán nhãn](../docs/annotation-guide.md). Bộ này dành cho đối chứng tiếng Anh, tách khỏi train/validation/test tiếng Việt.

## Độ phủ gán nhãn

| Nhãn | Số vùng vàng | Số ghi chú có nhãn | Tình huống |
|---|---:|---:|---|
| NAME | 14 | 9 | Người bệnh, người thân, người chăm sóc, bác sĩ; tên lặp, viết thường, viết hoa, dấu nối, dấu nháy và dấu tổ hợp |
| DOB | 5 | 4 | Ngày dạng số, ISO, tháng bằng chữ và năm sinh riêng; có ngày khám khác để đối chiếu |
| PHONE | 4 | 4 | Mã nước, ngoặc, dấu chấm hoặc dấu nối; có số sê-ri giống số điện thoại ở mẫu âm |
| ID | 5 | 3 | MRN, mã người bệnh, số hồ sơ có số 0 đầu và số hộ chiếu giả lập |
| ADDR | 4 | 3 | Địa chỉ cũ/mới, căn hộ hoặc phòng, viết tắt, dấu phẩy nội bộ và địa chỉ qua CRLF |

Tổng cộng 32 vùng. `en-011`–`en-013` là ba ghi chú âm hoàn toàn, bao phủ ngày khám, mã ICD, số phòng, chỉ số, thuốc, tuổi, năm không có ngữ cảnh sinh, tên cơ sở và số sê-ri thiết bị.

## Ví dụ ranh giới

| Ghi chú | Nhãn và khoảng | Giá trị được gán |
|---|---|---|
| `en-001` | `NAME [9,19)`, `DOB [26,36)`, `ID [43,53)` | `Mara Quill`, `07/14/1986`, `MRN-004218`. Ngày khám `11/21/2026` nằm ngoài vùng. |
| `en-003` | `ADDR [34,80)` | `48 Kestrel Spire Ave., Apt. 4B,\r\nBriarwick, ZZ`. Giữ dấu chấm viết tắt, dấu phẩy và CRLF bên trong. |
| `en-005` | `NAME [22,30)` | `Zoe\u0308 Ash` có dấu tổ hợp. Emoji trước vùng chiếm một code point. |
| `en-008` | `NAME [9,17)`, `[70,78)`, `[127,135)` | Hai lần `Ada Rune` và một lần `ada rune` đều có span riêng. |
| `en-012` | `[]` | `2025550109` là số sê-ri máy xét nghiệm theo ngữ cảnh. |
| `en-016` | `DOB [4,14)` và `[117,128)` | `1990-04-09` và `09 Apr 1990` đều được nêu là ngày sinh. Ngày đo ECG và mã tham chiếu ECG nằm ngoài vùng. |

Trong bảng, `\r\n` và `\u0308` biểu diễn ký tự gốc để tiện đọc. Khi đối chứng, chỉ ánh xạ nhãn upstream có tương đương; báo vùng che theo `redaction_region` riêng với `exact_span_label`. Bản khóa này chưa kèm kết quả chạy hay điểm.

## Khóa dữ liệu

SHA-256 của JSONL UTF-8 không BOM, phân cách dòng bằng LF và có LF cuối file:

```text
100083a44fb393c1661c77c69a13f41d52907a3e2d7cfd94f1c331d1089d879a
```

Chạy từ thư mục gốc. Chuẩn hóa CRLF vật lý do Git chuyển khi checkout Windows. Các escape JSON trong `text` giữ nguyên.

```powershell
.\.venv\Scripts\python.exe -c "import hashlib; from pathlib import Path; data = Path('data/english.jsonl').read_bytes().replace(b'\r\n', b'\n'); print(hashlib.sha256(data).hexdigest())"
```

BA đã tự kiểm cấu trúc 16 dòng, ID và họ duy nhất, đủ năm nhãn, ranh giới không chồng lấn và slice khớp giá trị đã chọn. QA đối chiếu nhãn và ranh giới trực tiếp với từng ghi chú trước khi dùng làm bộ đối chứng. Nếu cần sửa sau review, ghi lý do gán nhãn, tăng revision và khóa lại hash trước khi đánh giá.
