# Hỏi đáp bảo vệ MedShield

## Một mẫu là gì và có bao nhiêu mẫu?

Một mẫu là một ghi chú giả lập. Tiếng Việt có 100 ghi chú, gồm 60 train, 20 validation và 20 test. Test có 33 vùng định danh vàng. Tiếng Anh có 16 ghi chú và 32 vùng vàng. Tập tiếng Việt tách theo họ câu để các biến thể cùng cấu trúc không nằm cả trong train và test. Hồ sơ dự án ghi 0 mẫu do chủ dự án trực tiếp rà soát. Manifest và biên bản ghi các lượt gán nhãn/kiểm của agent.

## AI nằm ở đâu và dùng mô hình có sẵn hay tự huấn luyện?

Thư viện `sklearn-crfsuite` cung cấp thuật toán huấn luyện. `ml/train.py` fit mô hình từ đặc trưng token và nhãn BIO của dữ liệu dự án, rồi chọn cấu hình bằng validation. Trọng số kết quả nằm ở `artifacts/model/model.crfsuite`. Khi phân tích, `ml/model.py` nạp trọng số để dự đoán NAME và ADDR. Hybrid hợp kết quả với quy tắc xử lý cả DOB, PHONE và ID.

## Vì sao dùng ba công cụ đối chứng?

Để đo ba công cụ có đặc tính khác nhau trên cùng 16 ghi chú tiếng Anh. Presidio, Philter UCSF và GEMINI pyDeid lần lượt đạt 59,14%, 78,21% và 56,20% micro-F1 vùng che. Đơn vị là vị trí ký tự ngoài khoảng trắng. Web dùng rules/CRF/hybrid của dự án cho bài toán tiếng Việt.

## Nhãn nào khó và biết kết quả tốt hay chưa bằng cách nào?

Trên test tiếng Việt, DOB và PHONE có F1 bằng 0 ở cả ba cấu hình, với mỗi nhãn 4 vùng vàng. NAME đạt 69,23% ở NER/hybrid. ADDR đạt 100% ở NER/hybrid với 3 vùng vàng. NER có micro-F1 cao nhất 53,33%, còn hybrid 52,00%. Exact span + label yêu cầu hai biên và nhãn cùng đúng. Hybrid có TP 13, FP 4, FN 20 nên F1 là `26/(26+4+20) = 52%`. Kết luận quy trình đánh giá đã kiểm chứng. Mục tiêu F1 ≥85% trên đủ năm nhãn vẫn chưa đạt.

## Khi nào phải rà soát bằng tay?

Trước mọi lần xuất để chia sẻ. Hybrid còn bỏ sót ít nhất một vùng trong 11/20 ghi chú test. Người dùng cần xem tên viết thường, số trông giống điện thoại và biên địa chỉ. Ca demo có `tạ hư cấu` bị sót. Thêm vùng NAME rồi xuất, đối chiếu `[NAME_2]` và ngày tái khám `18/12`.

## Vì sao dùng PDF.js và cần để ý giới hạn gì?

PDF.js trích chữ tại trình duyệt rồi đưa vào ô nhập. FastAPI nhận phần chữ sau khi bấm Phân tích. Ảnh scan cần OCR riêng. Với biểu mẫu nhiều cột, so lại thứ tự các trường trước khi phân tích. Kết quả hiện xuất TXT/JSON. PDF giả lập để demo có hai trang.

## Tôi trình bày đóng góp thế nào?

“Em thực hiện đề tài cá nhân với hỗ trợ Codex và Claude. Phần em có thể giải thích và trình diễn là dữ liệu giả lập, quy ước nhãn, pipeline huấn luyện CRF, cách gộp rules/NER, bộ đo và luồng người dùng rà soát rồi xuất. Em dùng lại React, FastAPI, PDF.js và sklearn-crfsuite, ghi nguồn trong repo.”

Nguồn số liệu: [Báo cáo thực nghiệm](experiment.md) · [Artifact](../artifacts/evaluation.json) · [Biên bản PDF](reviews/G4-pdf.md).
