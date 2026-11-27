# Các chế độ phân tích MedShield

| Chế độ | Ngôn ngữ | Phát hiện | Nguồn trên từng vùng |
|---|---|---|---|
| Quy tắc (`rules`) | Việt, Anh | Mẫu có ngữ cảnh cho NAME, DOB, PHONE, ID và ADDR. Bản tiếng Việt có kiểm lịch, kiểm cấu trúc số và khớp từ dẫn không dấu. | `medshield-rules` hoặc `medshield-rules+exact-name-repeat` (tiếng Việt) |
| NER (`ner`) | Việt | CRF tuyến tính dự đoán chuỗi nhãn BIO cho NAME và ADDR. Cần trọng số do MedShield huấn luyện với ghi chú giả lập. | `medshield-crf` |
| Kết hợp (`hybrid`) | Việt | Chạy CRF và quy tắc trên cùng nguyên văn rồi gộp đề xuất. | `medshield-crf`, `medshield-rules` hoặc `medshield-rules+exact-name-repeat` |

Hybrid gộp các đề xuất trước khi giải quyết giao nhau. DOB, PHONE và ID có neo ngữ cảnh từ quy tắc được ưu tiên cao nhất. Khi có giao nhau ở NAME/ADDR, ưu tiên CRF trong lúc chờ hiệu chuẩn từ dữ liệu độc lập. Hybrid giữ các vùng CRF có score thấp và đã bỏ cơ chế rule bao trọn ghi đè. Tên có điểm từ 0,90 làm mốc đề xuất các lần trùng nguyên văn tiếp theo trong ghi chú. Giữ các vùng trực tiếp trước vùng tên lặp. Cùng mức ưu tiên, giữ điểm cao hơn rồi vùng dài hơn. API trả vùng đã chọn theo thứ tự xuất hiện.

PHONE có từ dẫn rõ được đề xuất dù giá trị ngoài dải; kiểm cấu trúc chỉ cộng điểm. PHONE đứng riêng có nguồn `medshield-rules+phone-standalone` khi đủ tín hiệu và `medshield-rules+phone-review` khi cần đưa lên đầu hàng rà soát. Đề xuất trong hàng chờ có thể bỏ trước xác nhận, và mặc định được che trong bản xem trước. [Kết quả hồi quy Q2](phase-q2.md)

`/health` kiểm khả năng nạp mô hình. Khi thiếu trọng số hoặc metadata hợp lệ, `vi/ner` và `vi/hybrid` hiện `unavailable` và yêu cầu phân tích trả `503 ENGINE_UNAVAILABLE`. `en/ner` và `en/hybrid` luôn chưa hỗ trợ. `MEDSHIELD_MODEL_DIR` cho phép chỉ định thư mục artifact khác. Mặc định API tìm mô hình trong `artifacts/model`.

Presidio, Philter UCSF và GEMINI pyDeid được thử độc lập cho đối chứng tiếng Anh. Bảng này mô tả các chế độ người dùng thực sự gọi qua API cục bộ.
