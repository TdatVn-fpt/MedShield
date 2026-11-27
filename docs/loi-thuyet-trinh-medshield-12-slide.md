# Lời thuyết trình MedShield · 12 slide và demo web

Nguyễn Tiến Đạt · Samsung Innovation Campus · AI-NIC4 · Đề tài số 2

Dành khoảng 6–7 phút cho slide 1–11 và 3 phút cho demo ở slide 12. Phần **Lời nói** là kịch bản để tập đọc. Dòng **Chỉ trên màn hình** giúp bạn biết lúc nào cần chỉ vào slide hoặc chuyển sang trình duyệt. Mỗi trang PowerPoint có cùng phần lời nói trong **Notes**.

## Slide 1 · MedShield và mục tiêu trình bày

**Chỉ trên màn hình** — Tên dự án và đề tài số 2.

**Lời nói**

> Em chào thầy. Em là Nguyễn Tiến Đạt, lớp AI-NIC4. Em làm đề tài số 2, nhận diện và che thông tin định danh trong văn bản y tế. Em chọn làm một website để người dùng vừa xem được máy phát hiện gì, vừa sửa được chỗ máy bỏ sót trước khi tải kết quả. Em sẽ giải thích từ bài toán, cách em kết hợp mô hình với quy tắc, đến kết quả đo và một lượt demo trên web.

## Slide 2 · Bối cảnh và bài toán

**Chỉ trên màn hình** — Ví dụ tên và ngày tái khám.

**Lời nói**

> Giả sử em muốn chia sẻ một ghi chú để học. Các thông tin như triệu chứng và lịch tái khám vẫn có ích, còn tên hay mã bệnh nhân thì cần che trong phạm vi bài toán. Ví dụ, Mai An là tên cần che, còn 18/12 sau cụm hẹn khám lại cần giữ. Cùng là một chuỗi ngày tháng, ý nghĩa đổi tùy câu đứng trước. Em định nghĩa năm nhãn gồm tên người, ngày sinh, điện thoại, mã định danh và địa chỉ. Máy cần xác định cả đoạn cần che lẫn nhãn của đoạn đó.

## Slide 3 · Luồng sử dụng

**Chỉ trên màn hình** — Trình tự nhập, phân tích, rà soát và xuất.

**Lời nói**

> Người dùng có thể dán văn bản, nhập TXT hoặc trích chữ từ PDF. Khi bấm Phân tích, web hiển thị vùng gốc có đánh dấu và bản xem trước. Người dùng có thể bấm một phát hiện để tìm vị trí, đổi nhãn, xóa vùng sai hoặc bôi đen một đoạn còn sót để thêm. Mỗi lần sửa, web cập nhật bản che. Người dùng xác nhận rồi mới tải TXT hoặc JSON. Nếu sửa văn bản gốc thì kết quả cũ mất hiệu lực, kể cả khi phản hồi cũ về muộn.

## Slide 4 · Kiến trúc hệ thống

**Chỉ trên màn hình** — Đi từ React sang FastAPI, rồi xuống service và adapter.

**Lời nói**

> React hiển thị giao diện, TypeScript mô tả dữ liệu, Vite chạy môi trường phát triển và build. Với PDF, PDF.js trích chữ trong trình duyệt. Khi bấm Phân tích, hook useReview gửi văn bản và chế độ đến FastAPI. Nếu hình dung theo ASP.NET MVC, React đảm nhiệm phần View. Controller nhận yêu cầu, schema Pydantic kiểm dữ liệu, service thực hiện nghiệp vụ và adapter gọi bộ nhận diện. Kết quả chung là một danh sách có vị trí, nhãn và nguồn. Khi người dùng sửa kết quả, web gọi API redact để tạo lại bản che từ danh sách đã sửa.

## Slide 5 · Lý do chọn và đóng góp

**Chỉ trên màn hình** — Hai nhóm thư viện tận dụng và phần MedShield triển khai.

**Lời nói**

> Em tận dụng React và FastAPI để làm giao diện và API, PDF.js để đọc lớp chữ, còn sklearn-crfsuite cung cấp thuật toán CRF chạy CPU. Phần triển khai của MedShield là thiết kế nhãn và dữ liệu giả lập, viết đặc trưng cho tiếng Việt, huấn luyện trọng số, viết quy tắc, ghép vùng, xây luồng rà soát và đo kết quả. Đây là đồ án cá nhân có hỗ trợ từ Codex và Claude. Presidio, Philter và pyDeid được dùng trong bài đối chứng tiếng Anh riêng.

## Slide 6 · Quy tắc theo ngữ cảnh

**Chỉ trên màn hình** — Hai trường hợp ngày sinh và ngày tái khám.

**Lời nói**

> Baseline dùng quy tắc để em có một mốc so sánh dễ kiểm tra. Regex nhận các mẫu chữ và số. Với ngày sinh, em xét từ dẫn như “sinh ngày”, vì ngày khám và ngày sinh có thể cùng được viết theo kiểu ngày, tháng, năm. Quy tắc ngắn dễ giải thích nhưng phụ thuộc cách người ta viết. Trong tập test, số 0900000041 là số lưu kho, có hình dạng giống số điện thoại, nên máy che nhầm. Đây là một FP, tức một dự đoán thừa.

## Slide 7 · CRF và nhãn BIO

**Chỉ trên màn hình** — Ví dụ Hạ là B-NAME, Minh là I-NAME.

**Lời nói**

> CRF là mô hình học có giám sát để gán nhãn cho một chuỗi. Em tách câu thành token, chuẩn bị đặc trưng như viết hoa, tiền tố, hậu tố và các token lân cận. BIO đánh dấu đầu vùng, phần tiếp theo và phần ngoài vùng. Ví dụ, Hạ là B-NAME, Minh là I-NAME. Khi huấn luyện, mô hình học từ 60 ghi chú đã gán nhãn, rồi dùng 20 ghi chú validation để chọn cấu hình. Web dùng trọng số đã huấn luyện của dự án để dự đoán NAME và ADDR. Bấm Phân tích là chạy dự đoán, còn huấn luyện được thực hiện bằng script riêng.

## Slide 8 · Cách gộp Hybrid

**Chỉ trên màn hình** — Thứ tự ưu tiên khi hai vùng giao nhau.

**Lời nói**

> Cả quy tắc và CRF nhận cùng một văn bản gốc. Đầu ra mỗi bên được đưa về một định dạng. Với các vùng chồng nhau, em ưu tiên quy tắc cho ngày sinh, điện thoại và mã, sau đó đến CRF cho tên và địa chỉ, rồi đến ứng viên tên hoặc địa chỉ từ quy tắc. Các vùng không chồng vẫn có thể cùng được giữ. Sau khi chốt vùng, hệ thống mới thay chữ bằng ký hiệu. Nhờ trường nguồn, em có thể giải thích vùng nào do quy tắc, mô hình hay người dùng đưa vào.

## Slide 9 · Dữ liệu và phép chấm

**Chỉ trên màn hình** — 100 ghi chú, phân chia 60/20/20 và 33 vùng vàng trên test.

**Lời nói**

> Một mẫu là một ghi chú giả lập, có thể có nhiều vùng cần che hoặc không có vùng nào. Em chia 100 ghi chú thành 60 để huấn luyện, 20 để chọn cấu hình và 20 để chấm cuối. Việc chia theo họ câu giúp các biến thể cùng một khuôn không rơi vào cả tập học và tập test. Test có 33 vùng vàng, tức đáp án đã gán. Một vùng được tính đúng khi khớp cả điểm đầu, điểm cuối và nhãn. Em cộng TP, FP và FN trên toàn bộ test để tính micro-F1, dùng dự đoán trước khi người dùng sửa.

## Slide 10 · Kết quả tiếng Việt

**Chỉ trên màn hình** — Đọc ba điểm và chỉ cột số ghi chú còn sót.

**Lời nói**

> Trên 20 ghi chú tiếng Việt, Rules đạt 4,76%, CRF đạt 53,33% và Hybrid đạt 52% micro-F1. So với CRF, Hybrid thêm một mã bệnh nhân đúng và bốn số bị che nhầm, nên số ghi chú còn sót giảm từ 12 xuống 11 nhưng F1 giảm. Cụ thể, Hybrid có 13 vùng đúng, 4 vùng thừa và 20 vùng sót. Địa chỉ đạt 100% ở CRF và Hybrid trên đúng ba vùng vàng. Mục tiêu F1 85% trên đủ năm nhãn chưa đạt. Em giữ bước rà soát vì trên test vẫn còn nhiều vùng sót.

## Slide 11 · Đối chứng tiếng Anh

**Chỉ trên màn hình** — Ba công cụ và chú thích “vùng che”.

**Lời nói**

> Em dùng Presidio, Philter UCSF và GEMINI pyDeid để có thêm một bài đối chứng bằng công cụ mã nguồn mở. Cả ba đọc độc lập cùng 16 ghi chú tiếng Anh giả lập. Vì đầu ra khác nhau, em quy về các vị trí ký tự được che, bỏ khoảng trắng khi tính. Kết quả lần lượt là 59,14%, 78,21% và 56,20%. Philter có F1 vùng che cao nhất trong lần chạy này, đồng thời vẫn còn ít nhất một vị trí sót trên 12 ghi chú. Bài tiếng Việt chấm cả biên vùng và nhãn, nên hai bảng có đơn vị khác nhau.

## Slide 12 · Demo và kết luận

**Chỉ trên màn hình** — Mở website khi bắt đầu đoạn này. Xem thao tác theo thời gian ngay bên dưới.

**Lời nói**

> Em chuyển sang web và mở PDF bệnh án ngoại trú hai trang. Đây là dữ liệu giả lập. Em chọn trang 1 đến 2, bấm Trích văn bản. Bây giờ chữ đã xuất hiện ở ô Văn bản gốc. PDF được đọc trong trình duyệt. Văn bản được gửi tới API khi em bấm Phân tích.
>
> Em chọn Kết hợp, tức Hybrid, và bấm Phân tích. Bên này là các vùng máy phát hiện, bên kia là bản đã che. Thầy xem dòng Đi cùng. Cụm “tạ hư cấu” là tên người đi cùng trong mẫu. Máy bỏ sót tên viết thường này, nên nó vẫn xuất hiện nguyên văn.
>
> Em bôi đen đúng cụm “tạ hư cấu” trong văn bản có đánh dấu, chọn NAME rồi bấm Thêm vùng che. Bản xem trước đã đổi thành [NAME_2]. Lúc này vùng mới có nguồn do người dùng thêm. Em rà soát toàn bộ rồi xác nhận và tải TXT.
>
> Em mở file vừa tải. Dòng Đi cùng đã được che bằng [NAME_2]. Dòng Hẹn tái khám 18/12 vẫn giữ. Ca này cho thấy máy hỗ trợ tìm vùng, người dùng có thể sửa chỗ sót và xem chính xác nội dung sẽ được chia sẻ.

## Chuẩn bị trước khi mở slide

1. Khởi động API và web theo [README Windows](../README.md#chạy-nhanh-trên-windows). Giữ hai terminal mở.
2. Mở [website](http://127.0.0.1:5173/) và [API health](http://127.0.0.1:8000/health). Kiểm tra `vi/hybrid` có trạng thái `available` rồi quay về tab web.
3. Chuẩn bị [PDF ngoại trú hai trang](evidence/demo-benh-an-ngoai-tru.pdf), [TXT dự phòng](evidence/demo-benh-an-ngoai-tru.txt) và mở sẵn thư mục Downloads. Dùng tệp PDF trong repo để khớp ca đã kiểm thử.

## Điều khiển demo web trong 3 phút

| Thời gian | Bạn làm gì | Kiểm tra ngay trên màn hình |
|---|---|---|
| 0:00–0:40 | Chuyển sang web. Bấm **Nhập PDF**, chọn `demo-benh-an-ngoai-tru.pdf`, để **Trang đầu** 1, **Trang cuối** 2 rồi bấm **Trích văn bản**. Đọc đoạn 1 của slide 12. | Ô **Văn bản gốc** có nội dung hai trang. Nhìn nhanh phần hành chính và dòng hẹn tái khám. |
| 0:40–1:20 | Chọn **Tiếng Việt** và phương pháp **Kết hợp · hybrid**. Bấm **Phân tích**, kéo đến dòng **Đi cùng**. Đọc đoạn 2. | Có vùng đánh dấu. Tên viết thường trong dòng **Đi cùng** vẫn xuất hiện. |
| 1:20–2:25 | Bôi chuột đúng `tạ hư cấu` ở **Văn bản gốc có đánh dấu**, bỏ dấu chấm ngoài lựa chọn. Chọn `NAME`, bấm **Thêm vùng che**. Đọc đoạn 3. Chờ bản xem trước cập nhật rồi tích **Tôi đã rà soát toàn bộ nội dung** và bấm **Tải TXT**. | Có vùng mới do người dùng thêm. Dòng đã đổi thành `Đi cùng: [NAME_2].`. |
| 2:25–3:00 | Mở file vừa tải từ danh sách tải xuống của trình duyệt. Đọc đoạn 4. | Chỉ vào `Đi cùng: [NAME_2].` và `Hẹn tái khám: 18/12.` trong **file tải xuống**. |

Nếu thầy muốn xem bằng chứng số liệu trên web, bấm **Thực nghiệm** sau khi đã tải file, rồi chỉ vào bảng tiếng Việt và tiếng Anh. Trang đọc artifact qua API, không huấn luyện lại tại chỗ. Nguồn đối chiếu là [artifact tổng hợp](../artifacts/evaluation.json) và [báo cáo thực nghiệm](experiment.md).

Nếu PDF không trích được chữ, dùng **Tải TXT lên** với [mẫu dự phòng](evidence/demo-benh-an-ngoai-tru.txt) rồi tiếp tục từ bước phân tích. Bạn có thể nói “Em dùng bản TXT của cùng ca để minh họa bước rà soát. Bản hiện tại hỗ trợ PDF có lớp chữ và xuất kết quả dạng TXT hoặc JSON.” Nếu cần đối chiếu, mở [bản TXT đã xuất trong ca QA](evidence/demo-benh-an-ngoai-tru.reviewed.txt) và gọi rõ đó là file lần kiểm trước.

## Nếu thầy hỏi thêm

| Câu hỏi | Câu trả lời ngắn |
|---|---|
| AI nằm ở đâu? | “CRF học cách gán nhãn chuỗi cho tên và địa chỉ. Code huấn luyện ở `ml/train.py`, trọng số ở `artifacts/model/model.crfsuite`, và đường dự đoán đi qua `apps/api/adapters/ner.py`.” |
| CRF có sẵn hay tự huấn luyện? | “Thuật toán và hàm fit là của thư viện sklearn-crfsuite. Trọng số được fit từ 60 ghi chú train của MedShield. Validation dùng để chọn cấu hình trước khi chấm test.” |
| Vì sao địa chỉ 100% mà điểm chung vẫn thấp? | “Test chỉ có ba vùng địa chỉ. Micro-F1 tính trên toàn bộ vùng và năm nhãn, nên nhiều chỗ sót ở các nhãn khác vẫn kéo điểm chung xuống.” |
| Vì sao dùng Hybrid khi F1 thấp hơn? | “Ở ca đo này, Hybrid tìm thêm một mã đúng và tăng số che nhầm. Demo dùng Hybrid để minh họa hai nguồn dự đoán và cách người dùng rà soát. Kết quả test cho thấy phần quy tắc còn cần cải thiện.” |
| PDF gửi lên server hay chạy trong trình duyệt? | “PDF.js đọc tệp tại trình duyệt. Khi bấm Phân tích, API nhận văn bản đã trích. PDF dạng ảnh cần OCR, còn phiên bản demo cần lớp chữ.” |
| Có thể dùng ngay với bệnh án thật không? | “Em mới đánh giá với dữ liệu giả lập, trên năm nhãn và tập test nhỏ. Bước tiếp theo là đánh giá trên dữ liệu được phép sử dụng, nâng độ phủ và xác nhận quy trình kiểm tra trước khi chia sẻ.” |

## Nguồn để mở khi thầy hỏi

| Chủ đề | Nguồn |
|---|---|
| Repo và cách chạy | [GitHub · nhánh demo](https://github.com/TdatVn-fpt/MedShield/tree/feat/medshield-demo) · [README](../README.md) |
| Kiến trúc và đường đi API | [Sơ đồ](architecture.md) · [Hợp đồng API](api-contract.md) · [React hook](../apps/web/src/useReview.ts) · [Controller](../apps/api/controllers.py) · [Service phân tích](../apps/api/services/analysis.py) · [Hàm che](../apps/api/services/redaction.py) |
| Quy tắc và gộp vùng | [Phạm vi engine](engines.md) · [Rule adapter](../apps/api/adapters/rules.py) |
| CRF và dữ liệu học | [Script train](../ml/train.py) · [Đặc trưng](../ml/features.py) · [Metadata mô hình](../artifacts/model/metadata.json) · [CRFsuite upstream](https://www.chokkan.org/software/crfsuite/) |
| Luồng PDF | [Mã trích chữ](../apps/web/src/pdfDocument.ts) · [Tài liệu PDF.js](https://mozilla.github.io/pdf.js/) · [Test luồng PDF → sửa → xuất](../apps/web/e2e/pdf-import.spec.ts) · [Biên bản PDF](reviews/G4-pdf.md) |
| Chứng minh số liệu | [Tập test đã khóa](../data/test-manifest.json) · [Cách tính điểm](../ml/scoring.py) · [Tiếng Việt](../artifacts/evaluation-vi.json) · [Tiếng Anh](../artifacts/evaluation-en.json) · [Báo cáo thực nghiệm](experiment.md) |
| Ba công cụ tiếng Anh | [Cấu hình và phiên bản của MedShield](upstream.md) · [Presidio](https://github.com/data-privacy-stack/presidio) · [Philter UCSF](https://github.com/BCHSI/philter-ucsf) · [GEMINI pyDeid](https://github.com/GEMINI-Medicine/pyDeid) |
