# Các chế độ phân tích MedShield

| Chế độ | Ngôn ngữ | Phát hiện | Nguồn trên từng vùng |
|---|---|---|---|
| Quy tắc (`rules`) | Việt, Anh | Các mẫu có ngữ cảnh cho NAME, DOB, PHONE, ID và ADDR. Dùng như baseline tiếng Việt. | `medshield-rules` |
| NER (`ner`) | Việt | CRF tuyến tính dự đoán chuỗi nhãn BIO cho NAME và ADDR. Cần trọng số do MedShield huấn luyện với ghi chú giả lập. | `medshield-crf` |
| Kết hợp (`hybrid`) | Việt | Chạy CRF và quy tắc trên cùng nguyên văn rồi gộp đề xuất. Quy tắc xử lý DOB, PHONE, ID và bổ sung NAME/ADDR ngoài vùng của CRF. | `medshield-crf` hoặc `medshield-rules` |

Trong chế độ kết hợp, vùng quy tắc của DOB, PHONE và ID có ưu tiên cao nhất. Tiếp theo là NAME và ADDR từ CRF, sau đó là NAME và ADDR từ quy tắc. Cùng mức ưu tiên, giữ điểm cao hơn rồi vùng dài hơn. Khi hai vùng giao nhau, vùng đứng trước theo thứ tự ưu tiên được giữ nguyên. API trả vùng đã chọn theo thứ tự xuất hiện. Điểm CRF và điểm quy tắc dùng để sắp trong cùng mức ưu tiên.

`/health` kiểm khả năng nạp mô hình. Khi thiếu trọng số hoặc metadata hợp lệ, `vi/ner` và `vi/hybrid` hiện `unavailable` và yêu cầu phân tích trả `503 ENGINE_UNAVAILABLE`. `en/ner` và `en/hybrid` luôn chưa hỗ trợ. `MEDSHIELD_MODEL_DIR` cho phép chỉ định thư mục artifact khác. Mặc định API tìm mô hình trong `artifacts/model`.

Presidio, Philter UCSF và GEMINI pyDeid được thử độc lập cho đối chứng tiếng Anh. Bảng này mô tả các chế độ người dùng thực sự gọi qua API cục bộ.
