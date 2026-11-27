# MedShield · Kịch bản slide bảo vệ

Sáu slide, định dạng 16:9. Dùng PDF giả lập cho demo. Nếu thời gian trình bày ngắn, từ slide 1 đến 5 nói khoảng 3 phút, rồi dùng 3 phút cho slide 6 và demo thật.

[Lời thuyết trình đầy đủ để đọc tập](loi-thuyet-trinh-medshield.md) giải thích lý do chọn công nghệ, kiến trúc từng tầng, cách kết hợp rules và CRF, cách đọc số liệu và phần hỏi sâu.

## 1. Nhận diện và che thông tin định danh trong văn bản y tế

**Trên slide:** MedShield · Nguyễn Tiến Đạt · Samsung Innovation Campus AI-NIC4 · Đề tài số 2.

**Lời nói:** “Khi lấy một ghi chú y tế làm ví dụ học tập, em cần giữ phần chuyên môn và che những chi tiết có thể nhận ra người bệnh. MedShield đề xuất các vùng cần che để người dùng kiểm tra trước khi xuất.”

## 2. Từ ghi chú đến bản đã rà soát

**Trên slide:** TXT hoặc PDF có chữ → phân tích `NAME`, `DOB`, `PHONE`, `ID`, `ADDR` → sửa vùng → xác nhận → TXT/JSON.

**Dòng kiến trúc để bổ sung khi chỉnh slide:** `React + PDF.js` → `FastAPI / Pydantic` → `Service` → `Rules + CRF` → `React rà soát` → `TXT / JSON`.

**Lời nói:** “Web đọc phần chữ của PDF ngay trong trình duyệt. Khi bấm phân tích, FastAPI nhận phần chữ. Mỗi vùng có vị trí, nhãn và nguồn. Sau khi sửa vùng, người dùng xem bản che mới rồi mới được tải xuống.”

## 3. Mô hình CRF học từ dữ liệu MedShield

**Trên slide:** `60 train / 20 validation / 20 test` · tách theo họ câu · `Hạ → B-NAME`, `Minh → I-NAME` · CRF xử lý NAME/ADDR, quy tắc bổ sung DOB/PHONE/ID.

**Lời nói:** “Em dùng sklearn-crfsuite để huấn luyện trọng số trên dữ liệu giả lập. Mô hình học từ hình dạng token, từ xung quanh và quan hệ giữa các nhãn. File CRF đã lưu được nạp để dự đoán, nên lúc demo hệ thống không huấn luyện lại. Em dùng validation chọn cấu hình rồi mới đo trên test riêng.”

## 4. Kết quả tiếng Việt và giới hạn

| Cấu hình | Micro-F1 | Ghi chú có FN |
|---|---:|---:|
| Rules | 4,76% | 15/20 |
| NER | 53,33% | 12/20 |
| Hybrid | 52,00% | 11/20 |

**Trên slide:** 20 ghi chú test, 33 vùng vàng, chấm exact span + label trước sửa tay. Mục tiêu 85% cho đủ 5 nhãn chưa đạt.

**Lời nói:** “Một vùng phải đúng nhãn và đúng cả hai biên mới tính là đúng. Hybrid có thêm một TP và bốn FP so với NER. Vì vậy nó bỏ sót trên ít ghi chú hơn, nhưng F1 giảm nhẹ. ADDR đạt 100% ở NER và hybrid trên ba vùng vàng, nên cần thêm dữ liệu để kết luận rộng hơn.”

## 5. Đối chứng tiếng Anh

**Trên slide:** 16 ghi chú, cùng nguyên văn, độ phủ vùng che theo ký tự. Presidio **59,14%**, Philter UCSF **78,21%**, GEMINI pyDeid **56,20%**. OCR và xuất PDF giữ bố cục nằm ngoài bản demo.

**Lời nói:** “Em cho ba công cụ nhận cùng văn bản giả lập và so vị trí che. Bài tiếng Anh dùng đơn vị ký tự, nên đọc riêng với F1 theo thực thể và nhãn của bài tiếng Việt. Đây là thí nghiệm đối chứng, còn web chạy quy tắc và CRF của MedShield.”

## 6. Demo một vùng bỏ sót

**Trên slide:** PDF trang 1–2 → Hybrid → thêm `NAME` → duyệt → tải TXT. Source: `github.com/TdatVn-fpt/MedShield`.

| Mốc demo | Thao tác và câu nói |
|---|---|
| 0:00–0:45 | Mở PDF giả lập, chọn hai trang và bấm **Trích văn bản**. Chỉ vào ngày tái khám `18/12`. |
| 0:45–1:20 | Chọn **Tiếng Việt / Kết hợp · hybrid**, bấm **Phân tích**, cho xem tên, ngày sinh và địa chỉ đã tô. |
| 1:20–2:25 | Bôi đen `tạ hư cấu`, chọn `NAME`, bấm **Thêm vùng che**. Giải thích tên viết thường trong ngữ cảnh này bị bỏ sót ở ca demo. |
| 2:25–3:00 | Xác nhận, tải TXT rồi mở file. Chỉ ra `[NAME_2]` và `18/12` còn nguyên. Nếu demo bị gián đoạn, mở [TXT đầu ra đã kiểm](evidence/demo-benh-an-ngoai-tru.reviewed.txt). |

**Kết:** “Kết quả của quy trình đánh giá tái tạo được. Chất lượng nhận diện còn cần cải thiện, nên MedShield giữ người dùng trong bước quyết định vùng nào sẽ che.”
