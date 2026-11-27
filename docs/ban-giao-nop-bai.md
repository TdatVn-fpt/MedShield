# Bộ nộp bài MedShield

**Nguyễn Tiến Đạt · Samsung Innovation Campus · AI-NIC4 · Đề tài số 2**

## Ba mục cần nộp

| Mục | Nội dung | Mở từ đâu |
|---|---|---|
| Source code | Repo GitHub, hướng dẫn chạy Windows, cây thư mục và cách tái tạo kết quả | [Nhánh nộp bài và README](https://github.com/TdatVn-fpt/MedShield/tree/feat/medshield-demo) |
| Slide | Sáu trang Canva khung 16:9 trình bày bài toán, CRF, kết quả và demo | [Xem trên Canva](https://www.canva.com/d/bqBLyVXeMF5kFoN) · [Lời thuyết trình từng slide](slides-nop-bai.md) |
| Docs | Báo cáo thực nghiệm, sơ đồ kỹ thuật, hướng dẫn demo và bằng chứng | Mục **Tài liệu theo nhu cầu** dưới đây |

Nếu giảng viên chưa có quyền xem repo hoặc Canva, cấp quyền xem theo cách lớp yêu cầu và kiểm tra bằng cửa sổ chưa đăng nhập tài khoản của bạn. Giữ bản tải xuống của slide để trình chiếu khi kết nối mạng chập chờn.

## Tóm tắt dự án

MedShield tìm và che năm nhóm định danh trong ghi chú y tế gồm tên, ngày sinh, điện thoại, mã định danh và địa chỉ. Người dùng nhập văn bản, TXT hoặc PDF có lớp chữ, rà soát trước khi tải TXT/JSON. Trình duyệt trích chữ PDF tại chỗ. FastAPI nhận chữ để chạy mô hình hoặc quy tắc. Mô hình CRF do dự án huấn luyện trên dữ liệu giả lập hỗ trợ NAME và ADDR.

Thí nghiệm tiếng Việt dùng 100 ghi chú chia 60/20/20 theo họ câu. Trên 20 ghi chú test có 33 vùng vàng, micro-F1 là **4,76% rules**, **53,33% NER** và **52,00% hybrid** với cách chấm exact span + label. Phương pháp hybrid giảm số ghi chú còn ít nhất một FN từ 12 xuống 11 so với NER, nhưng tăng từ 0 lên 4 FP. Mục tiêu F1 ≥85% cho đủ năm nhãn chưa đạt. Kết quả đối chứng tiếng Anh trên 16 ghi chú dùng đơn vị vùng che theo ký tự.

## Tài liệu theo nhu cầu

- **Giảng viên muốn chạy và kiểm:** [README](../README.md), [hướng dẫn Windows và demo](huong-dan-nhap-pdf.md), [biên bản nghiệm thu PDF](reviews/G4-pdf.md).
- **Giảng viên muốn kiểm phần AI:** [Báo cáo thực nghiệm](experiment.md), [số liệu máy đọc](../artifacts/evaluation.json), [metadata CRF](../artifacts/model/metadata.json), [đối chứng tiếng Anh](upstream.md).
- **Muốn xem code từ giao diện đến mô hình:** [Kiến trúc và Mermaid](architecture.md), [hợp đồng API](api-contract.md), [hướng dẫn gán nhãn](annotation-guide.md), [các chế độ](engines.md).
- **Đạt ôn bảo vệ:** [Lời thuyết trình đầy đủ](loi-thuyet-trinh-medshield.md), [hỏi đáp bảo vệ](defense-qa.md), [tài liệu tự học cho NotebookLM](medshield-hoc-va-bao-ve-notebooklm.md), [nội dung slide](slides-nop-bai.md).
- **Mẫu và đầu ra:** [PDF ngoại trú giả lập](evidence/demo-benh-an-ngoai-tru.pdf), [TXT nguồn](evidence/demo-benh-an-ngoai-tru.txt), [TXT đã che](evidence/demo-benh-an-ngoai-tru.reviewed.txt), [JSON đã che](evidence/demo-benh-an-ngoai-tru.reviewed.json).
- **Nguồn và phạm vi:** [Đóng góp](contributions.md), [Thư viện và giấy phép](../THIRD_PARTY.md), [Tiến độ](progress.md).

G0–G3 và PDF-01–PDF-04 đã qua nghiệm thu. Bộ nộp bài này mô tả phiên bản demo đã chạy. Trạng thái Three.js, CI, ZIP và các hạng mục G4/G5 xem trong bảng tiến độ. Slide và báo cáo sử dụng dữ liệu giả lập và không dùng kết quả demo cũ làm điểm phiên bản mới.
