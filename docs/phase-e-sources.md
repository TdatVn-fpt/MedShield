# Phase E — Thẩm định nguồn ứng viên

Ngày 26/11/2026. Chỉ đối chiếu tài liệu, giấy phép, commit và metadata cấu hình công khai. Chưa tải bản ghi, chọn test, gán nhãn, đo điểm hay thay thế test khóa. Quy trình và cổng tiếp nhận vẫn theo [Phase E](phase-e.md).

## Ứng viên đề xuất cho pilot học thuật

**Meddies PII v2, cấu hình `vietnamese`, commit `5dbe7cde649446028f628820c204bf53bb296894`.** Nhà phát hành mô tả đây là ghi chú tổng hợp về y tế và văn bản tổng quát, có nhãn theo vị trí ký tự. Hugging Face công bố 38.963 dòng tiếng Việt, một shard Parquet, và metadata báo nguồn công khai, không yêu cầu quyền truy cập trên Hub. Tổng số dòng chưa cho biết có bao nhiêu ghi chú y tế dùng được hay độ phủ năm nhãn. [Dataset card tại commit kiểm tra](https://huggingface.co/datasets/Meddies/meddies-pii-v2/blob/5dbe7cde649446028f628820c204bf53bb296894/README.md) · [Metadata cấu hình tiếng Việt](https://datasets-server.huggingface.co/info?dataset=Meddies%2Fmeddies-pii-v2&config=vietnamese)

Giấy phép khai báo là **CC BY-NC 4.0**. Nếu chủ dự án phê duyệt, dùng nguồn ứng viên cho đánh giá học thuật phi thương mại trong phạm vi đã ghi, giữ nguồn, revision, giấy phép và công bố các thay đổi khi dẫn lại. Nhà phát hành chỉ rõ mục đích thương mại cần liên hệ riêng. [Giấy phép CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) · [Giới hạn do nhà phát hành nêu](https://huggingface.co/datasets/Meddies/meddies-pii-v2#limits)

### Điều cần chứng minh trước khi chốt Phase E

- **Tách nhóm.** Cấu hình tiếng Việt công bố các trường `original_id`, `scenario`, `domain_profile`, `document_type`, `source` và `source_dataset`. Metadata chưa xác nhận có mã bệnh nhân hay họ mẫu đáng tin cho từng dòng của cấu hình này. `template_id` xuất hiện trong mô tả schema `eval-v2`; điều đó chưa chứng minh trường này có trong shard tiếng Việt đề xuất. QA phải đối chiếu lineage, quyết định nhóm bệnh nhân giả lập và họ sinh bằng bằng chứng, và loại phần không truy vết được. Số thứ tự dòng chỉ làm mã ghi chú, không dùng làm bằng chứng tách bệnh nhân hoặc họ.
- **Nhánh dữ liệu.** Chọn ghi chú thực sự thuộc miền y tế tiếng Việt từ shard đã khóa, hoặc phân loại riêng văn bản hành chính liên quan đến quy trình chăm sóc. Loại dữ liệu tổng quát ngoài phạm vi. Kiểm trùng nguồn và biến thể giữa validation, test, train dùng cho MedShield; cô lập các họ được đưa vào Phase E khỏi quá trình tinh chỉnh và lựa chọn checkpoint. Các cấu hình `eval*` là tập phát triển công khai của nhà phát hành và không tự đáp ứng yêu cầu test của MedShield.
- **Giữ gán mù.** Bỏ nhãn do nhà phát hành cung cấp khỏi gói cho người gán. Một biến thể `date` có thể là ngày khám hoặc ngày sinh; DOB chỉ gán khi đúng nghĩa. Tương tự, kiểm theo guideline đối với mã kỹ thuật, địa chỉ nơi khám và tên tổ chức. Không lấy nhãn sẵn hay dự đoán engine để làm vùng vàng. Chốt nhóm, lát và mẫu gán đôi trước khi xem kết quả người gán.
- **Quy mô và chất lượng.** Phải xác nhận đủ ≥150 ghi chú test và ≥800 vùng vàng, có đủ năm nhãn và các lát đã đăng ký. Validation phải có ≥100 vùng mỗi nhãn từ ≥3 họ. Hai người gán độc lập ít nhất 20% test, IAA strict ≥0,85 trước khi phân xử. Mẫu độc lập phi thương mại chỉ cho phép báo kết quả trên loại dữ liệu đó. Tính đại diện với hồ sơ thật cần bằng chứng riêng.
- **Kiểm trùng với mô hình.** Với checkpoint công khai đã học trên Meddies hoặc không xác minh được dữ liệu huấn luyện trùng với ứng viên, không dùng điểm từ nguồn này để đưa ra tuyên bố test độc lập cho checkpoint đó. Báo trạng thái chưa xác minh; giữ tập phù hợp riêng nếu cần để so sánh.

## Các nguồn so sánh

| Nguồn | Quyết định |
| --- | --- |
| PhoNER_COVID19 | Nguồn công khai có tên người, mã bệnh nhân, địa điểm và ngày trong tường thuật COVID-19. Phù hợp đối chiếu tagging tiếng Việt riêng. Không có bộ nhãn PHONE và DOB theo định nghĩa MedShield trong danh sách nhãn công bố. [Bài báo NAACL](https://aclanthology.org/2021.naacl-main.173/) |
| i2b2/n2c2 2014 | Đối chứng tiếng Anh có sẵn qua DBMI với DUA. Từng người phải có quyền truy cập do DBMI cấp. Chủ dự án cần tự hoàn tất thủ tục nếu dùng. [Danh mục dữ liệu của Harvard DBMI](https://n2c2.dbmi.hms.harvard.edu/data-sets) · [Bộ đọc XML cục bộ](i2b2-local.md) |
| Nhóm người biên soạn độc lập | Phương án dự phòng nếu shard công khai không chứng minh được nhóm hoặc không phù hợp giấy phép. Nhóm tạo nguồn không xem quy tắc hoặc test hiện có. Giữ cùng điều kiện gán đôi, phân xử và cổng nghiệm thu đã đăng ký. [Quy trình Phase E](phase-e.md) |

## Quyết định cần ghi

Chủ dự án chọn nguồn, phạm vi sử dụng và chỉ định người gán A, B cùng trọng tài. Với Meddies, bước kế tiếp sau phê duyệt là QA thẩm định subset nhỏ ở commit đã ghi, đối chiếu bằng chứng nhóm và xác nhận pipeline không đưa nhãn sẵn cho người gán. Nếu thiếu bằng chứng nhóm, dùng phần nguồn hợp lệ hoặc chuyển sang nhóm biên soạn độc lập. Việc chọn mô hình Phase M chờ Phase E đủ điều kiện theo quy trình.
