# Lời thuyết trình MedShield

**Nguyễn Tiến Đạt · Samsung Innovation Campus · AI-NIC4 · Đề tài số 2**

Bản đọc tập theo **sáu slide Canva hiện có**, khoảng **8 phút kể cả demo**. Mỗi mục có dòng **Trên slide** để biết bạn đang chỉ vào đâu, lời nói ở ngôi **em**, rồi một câu **chuyển slide**. Phần cuối dùng khi thầy hỏi sâu. Số liệu lấy từ bài đo của dự án, trước khi người dùng sửa tay.

## Slide 1 Bối cảnh và bài toán · 45 giây

**Trên slide:** MedShield · Nhận diện và che thông tin định danh trong văn bản y tế.

“Em chào thầy. Em là Nguyễn Tiến Đạt, lớp AI-NIC4. Đề tài của em là nhận diện và che thông tin định danh trong văn bản y tế.

“Bối cảnh là khi cần lấy một ghi chú y tế làm ví dụ cho học tập, trong cùng một đoạn có thể có cả thông tin chuyên môn lẫn tên người, số điện thoại hoặc mã bệnh nhân. Ví dụ, câu ‘Người bệnh Mai An, hẹn tái khám 18/12’ có tên cần rà soát để che và ngày hẹn cần giữ nguyên. Che quá ít có thể để sót định danh. Che quá nhiều có thể làm mất ý của ghi chú.

“Em đặt bài toán là tìm **đúng đoạn, đúng loại**, rồi để người dùng quyết định vùng nào sẽ được che. Em giới hạn ở năm nhãn: tên, ngày sinh, điện thoại, mã định danh và địa chỉ. Toàn bộ dữ liệu trong bài demo là giả lập.”

**Chuyển slide:** “Để làm được việc đó, em chia ứng dụng theo đường đi của một ghi chú.”

## Slide 2 Kiến trúc và luồng sử dụng · 1 phút 20 giây

**Trên slide:** Nhập TXT/PDF → nhận diện → người dùng sửa → xác nhận → TXT/JSON.

“Em chia hệ thống thành frontend React và backend FastAPI. React hiển thị bản gốc, danh sách phát hiện và bản đã che. TypeScript giúp em giữ kiểu dữ liệu nhất quán giữa các màn hình. Vite cung cấp môi trường chạy và build frontend.

“Khi chọn PDF, em tận dụng PDF.js để trích lớp chữ của các trang được chọn ngay trong trình duyệt. Người dùng xem và sửa phần chữ trước. Khi bấm **Phân tích**, web mới gửi chuỗi chữ, ngôn ngữ và chế độ tới `POST /api/analyze`.

“Ở backend, controller nhận HTTP, Pydantic kiểm dữ liệu, service chọn engine và adapter chuyển kết quả về một cấu trúc thống nhất. Mỗi vùng có vị trí đầu, vị trí cuối, nhãn và nguồn phát hiện. Web dựa vào đó để tô đúng chữ.

“Sau khi người dùng thêm, xóa hoặc đổi nhãn, web gửi danh sách vùng hiện tại tới `POST /api/redact`. Backend thay đoạn bằng ký hiệu như `[NAME_1]`. Người dùng kiểm tra bản đã che và xác nhận trước khi tải TXT hoặc JSON.”

**Sơ đồ để nhớ:** `React → FastAPI Controller → Schema → Service → Rules/CRF → Vùng phát hiện → Rà soát → TXT/JSON`.

**Chuyển slide:** “Phần kiến trúc vừa rồi giải thích dữ liệu đi đâu. Tiếp theo em giải thích vì sao phần nhận diện dùng hai cách.”

## Slide 3 Vì sao kết hợp quy tắc và CRF · 1 phút 35 giây

**Trên slide:** `60 train / 20 validation / 20 test` · BIO · CRF và rules.

“Điện thoại, ngày sinh và mã định danh thường có dạng chữ số hoặc từ dẫn khá rõ. Em dùng quy tắc có ngữ cảnh cho các trường này. Ví dụ, `sinh ngày` là dấu hiệu cho ngày sinh. Một ngày đứng sau `hẹn tái khám` cần được giữ trong ca demo. Ngược lại, tên và địa chỉ có nhiều cách viết và độ dài khác nhau. Em chọn CRF để học thêm tín hiệu từ ngữ cảnh.

“CRF là mô hình học có giám sát để gán nhãn cho một chuỗi token. Ví dụ trong `Họ và tên: Hạ Minh.`, em biểu diễn `Hạ` là `B-NAME`, tức bắt đầu tên; `Minh` là `I-NAME`, tức tiếp tục tên. Các token ngoài thực thể là `O`. Mô hình học từ đặc trưng như viết hoa, tiền tố, hậu tố và những từ lân cận. Khi dự đoán, em ghép chuỗi BIO lại thành vùng tên hoặc địa chỉ.

“Em tận dụng thư viện sklearn-crfsuite để fit mô hình. Trọng số được huấn luyện từ dữ liệu của MedShield và lưu trong `model.crfsuite`. Trong 100 ghi chú tiếng Việt giả lập, em dùng 60 để huấn luyện, 20 để chọn cấu hình và 20 để kiểm tra cuối. Em chia theo họ câu để tránh đánh giá trên các biến thể quá giống với dữ liệu huấn luyện. Khi bấm Phân tích, API nạp trọng số đã lưu để suy luận trên CPU.

“Trong hybrid, hai nguồn chạy trên cùng văn bản. Nếu vùng giao nhau, em ưu tiên quy tắc cho ngày sinh, điện thoại và mã định danh. Với tên và địa chỉ, em ưu tiên CRF trước ứng viên quy tắc. Kết quả vẫn ghi rõ vùng đến từ đâu.”

**Chuyển slide:** “Kết hợp hai nguồn có thể tìm thêm vùng và cũng có thể che nhầm thêm. Em đo cả hai trên cùng một tập test.”

## Slide 4 Đánh giá tiếng Việt · 1 phút

**Trên slide:** 20 ghi chú test · 33 vùng vàng · rules 4,76% · NER 53,33% · hybrid 52,00% micro-F1.

“Một mẫu của em là một ghi chú, có thể có nhiều định danh hoặc không có định danh. Em chấm trên 20 ghi chú test với 33 vùng đã gán nhãn. Em dùng exact span + label, nghĩa là hai biên và nhãn phải cùng đúng. Nếu hệ thống che đúng phần lớn địa chỉ nhưng lấy thêm chữ `cư trú:`, đó vẫn là một dự đoán sai biên và một vùng vàng chưa được khớp.

“Kết quả micro-F1 của rules là 4,76%, của NER là 53,33%, của hybrid là 52,00%. So với NER, hybrid có thêm một vùng đúng nhưng cũng thêm bốn vùng che nhầm. Số ghi chú còn ít nhất một vùng bỏ sót giảm từ 12 xuống 11, còn F1 giảm nhẹ. Hai số này trả lời hai câu hỏi khác nhau.

“Mục tiêu 85% trên đủ năm nhãn chưa đạt. ADDR đạt 100% ở NER và hybrid trên ba vùng vàng, nên em cần thêm mẫu trước khi kết luận rộng hơn. Kết quả này là lý do em giữ bước người dùng rà soát.”

**Chuyển slide:** “Ngoài bài đo tiếng Việt, em thử riêng ba công cụ trên văn bản tiếng Anh.”

## Slide 5 Tận dụng các công cụ đối chứng · 45 giây

**Trên slide:** Presidio **59,14%** · Philter UCSF **78,21%** · GEMINI pyDeid **56,20%**.

“Em tận dụng Presidio, Philter UCSF và GEMINI pyDeid để đối chứng. Ba công cụ chạy độc lập trên cùng 16 ghi chú tiếng Anh giả lập. Do đầu ra của chúng khác nhau, em quy về các vị trí ký tự thuộc vùng che, bỏ khoảng trắng, rồi tính F1. Presidio đạt 59,14%, Philter đạt 78,21% và pyDeid đạt 56,20% trong lần chạy này.

“Bài này đo theo ký tự. Bài tiếng Việt đo đúng đoạn và đúng nhãn. Khi trình bày, em nêu rõ tập dữ liệu và đơn vị để thầy đọc đúng từng bảng. Phần web tiếng Việt sử dụng rules và CRF của MedShield.”

**Chuyển slide:** “Em xin demo một ca để thấy rõ người dùng sửa kết quả như thế nào.”

## Slide 6 Demo nhập PDF sửa và xuất · 2 đến 3 phút

**Trên slide:** PDF trang 1–2 → Hybrid → thêm NAME → duyệt → tải TXT.

1. **Mở PDF và trích chữ.** “Đây là bệnh án ngoại trú hai trang do dự án làm giả lập. Em chọn trang 1 đến 2 và bấm **Trích văn bản**. Phần chữ xuất hiện để em đối chiếu trước khi gửi phân tích.”
2. **Bấm Phân tích.** “Em chọn Tiếng Việt và Kết hợp. Đây là các vùng máy đề xuất. Em có thể thấy nhãn và nguồn của từng vùng.”
3. **Sửa một vùng bị sót.** “Trong ca này, `tạ hư cấu` là tên giả của người đi cùng. Tên viết thường còn sót. Em bôi đen riêng tên, chọn `NAME` rồi bấm **Thêm vùng che**. Bản xem trước cập nhật thành `[NAME_2]`.”
4. **Xác nhận và mở file tải thật.** “Em kiểm lại toàn bộ, xác nhận và tải TXT. Trong file, phần tên vừa thêm đã được thay. Ngày tái khám `18/12` vẫn còn vì đây là nội dung cần giữ trong ca này.”

**Câu kết:** “MedShield đã chạy được luồng nhập, phát hiện, rà soát và xuất. Hướng cải thiện tiếp theo của em là bổ sung dữ liệu đa dạng cho những nhãn còn yếu và thử trên một tập đánh giá độc lập. Em cảm ơn thầy.”

## Nếu thầy hỏi sâu về kiến trúc

- **Controller, schema, service, adapter khác nhau thế nào?** `controllers.py` nhận HTTP. `schemas.py` định nghĩa và kiểm request. `services/analysis.py` quyết định chạy chế độ nào. `adapters/` đổi đầu ra rules và CRF về cùng kiểu Entity. `services/redaction.py` kiểm biên và thay vùng. Frontend dùng `useReview.ts` để quản lý bản đang rà soát và tránh phản hồi cũ ghi đè dữ liệu mới.
- **Vì sao phải thống nhất Unicode?** Python dùng vị trí code point theo khoảng `[start,end)`. JavaScript có thể đếm emoji bằng hai đơn vị UTF-16. Ví dụ `🙂 Mai An` có tên ở `[2,8)` theo code point và `[3,9)` theo UTF-16. Web quy đổi vị trí khi người dùng bôi đen để che đúng đoạn.
- **Vì sao không gửi PDF gốc?** Tận dụng PDF.js để trích lớp chữ tại trình duyệt và dùng chung luồng phân tích với TXT. Bản hiện tại hỗ trợ PDF có lớp chữ, xuất TXT/JSON. PDF scan cần OCR và xuất lại PDF giữ bố cục là phạm vi khác.
- **Hybrid có tốt hơn NER không?** Trong bài đo này, hybrid có recall **39,39%** so với **36,36%** của NER. Micro-F1 hybrid thấp hơn vì có thêm FP. Em dùng hybrid để demo đủ các loại trường và minh họa bước kiểm lại.
- **Cách tính F1 hybrid?** TP 13, FP 4, FN 20. F1 là `2 × 13 / (2 × 13 + 4 + 20) = 52%`. Thống kê `11/20` đếm ghi chú còn ít nhất một FN, còn `FN = 20` đếm số vùng bị sót.
- **Còn bao nhiêu nhãn chưa đạt?** Trong NER và hybrid, chỉ ADDR đạt ngưỡng 85% trên bộ test hiện tại. NAME đạt 69,23%. DOB và PHONE có F1 bằng 0 ở cả ba cấu hình. ID đạt 33,33% ở rules và hybrid.

## Tận dụng gì và đóng góp gì

- **Tận dụng:** React/TypeScript/Vite để làm web, FastAPI/Pydantic để làm API, PDF.js để đọc chữ PDF, sklearn-crfsuite để huấn luyện CRF. Presidio, Philter UCSF, GEMINI pyDeid phục vụ bài đối chứng.
- **MedShield triển khai:** Phạm vi năm nhãn, dữ liệu giả lập, các đặc trưng và quy trình huấn luyện, mẫu quy tắc theo ngữ cảnh, ưu tiên gộp vùng, hợp đồng Unicode, luồng rà soát và bài đánh giá có thể tái tạo.
- **Cách nói về vai trò:** “Em làm đề tài cá nhân với sự hỗ trợ Codex và Claude. Em trình bày quyết định kỹ thuật, số liệu và thao tác demo của phiên bản MedShield.” Hồ sơ hiện ghi 0 mẫu do chủ dự án trực tiếp rà soát. QA và BA đã đối chiếu tập test bằng quy trình của dự án.

## Tờ nhắc trước khi trình bày

**Bối cảnh → 5 nhãn → React/FastAPI → CRF + rules → 60/20/20 → 53,33% NER và 52,00% hybrid → sửa NAME → TXT vẫn có 18/12.**

Nếu quên lời, chỉ vào sơ đồ và tự hỏi: “Đầu vào của bước này là gì? Thành phần nào xử lý? Đầu ra là gì?” Khi tập, gạch dưới một cụm quan trọng mỗi slide. Sau một lượt đọc, tập lại chỉ nhìn tờ nhắc.

[Kiến trúc](architecture.md) · [Báo cáo thực nghiệm](experiment.md) · [PDF demo](evidence/demo-benh-an-ngoai-tru.pdf) · [TXT đã rà soát](evidence/demo-benh-an-ngoai-tru.reviewed.txt)
