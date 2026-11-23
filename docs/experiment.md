# Thực nghiệm MedShield — G3

**READY_FOR_REVIEW.** BA đối chiếu nhãn vàng, dự đoán và artifact tiếng Việt, tiếng Anh. QA và Tech Lead rà soát báo cáo.

Sáu dòng kết quả trong [artifact tổng hợp](../artifacts/evaluation.json) khớp với hai artifact nguồn.

## Dữ liệu và cách chấm

- **Tiếng Việt.** Đối chiếu `rules`, `ner` và `hybrid` trên cùng [tập test đã khóa](../data/test-manifest.json), trước khi có chỉnh sửa thủ công. Chấm theo tuple `(start, end, label)` trong từng `note_id`, với khoảng Unicode code point `[start,end)`. Một dự đoán sai biên hoặc sai nhãn tạo một FP và một FN. Micro cộng TP/FP/FN trước khi tính điểm. Báo số ghi chú có ít nhất một FN theo từng chế độ.
- **Tiếng Anh.** Presidio, Philter UCSF và GEMINI pyDeid nhận cùng giá trị `text` theo từng `note_id` trong [bộ đối chứng đã khóa](../data/english.md). Chấm `redaction_region` trên hợp vị trí code point ngoài whitespace của các vùng vàng và vùng công cụ tìm thấy. Kiểm căn vị trí mask Philter trên nguyên văn, gồm ca có CRLF và ký tự tổ hợp. [Phạm vi upstream](upstream.md)
- **Truy vết.** Đối chiếu hash, revision, số ghi chú, họ và support với JSONL và manifest. Gắn version/config của từng phương pháp và lệnh tái tạo đã chạy với artifact. [Hợp đồng đánh giá](api-contract.md#-get-apievaluation)

| Bộ dữ liệu đã đối chiếu | Ghi chú | Họ | Vùng vàng |
|---|---:|---:|---:|
| Tiếng Việt · train | 60 | 10 | 108 |
| Tiếng Việt · validation | 20 | 4 | 45 |
| Tiếng Việt · test | 20 | 6 | 33 |
| Tiếng Anh · đối chứng | 16 | 16 | 32 |

SHA-256 của bốn JSONL khớp bản khóa. Các tập tiếng Việt không trùng họ, ID hay nguyên văn. Train/validation `medshield-vi-synthetic-v2` dùng seed `20261121` cho dữ liệu sinh. Test `vi-test-v1` do QA soạn và BA kiểm độc lập. Test tiếng Việt có 17 NAME, 4 DOB, 4 PHONE, 5 ID, 3 ADDR. 32 vùng tiếng Anh quy thành 399 vị trí code point ngoài whitespace. Các tổng này mô tả nhãn vàng. [Manifest train/validation](../data/train-validation-manifest.json) · [Review nhãn test](reviews/G2-ba.md)

## Kết quả tiếng Việt

Kết quả `exact_span_label` trên 20 ghi chú test. BA đối chiếu lại 33 tuple vàng đã gán độc lập, khớp toàn bộ với nhãn QA. Sau đó gọi `/api/analyze` qua FastAPI TestClient cho 60 lượt ghi chú × chế độ. Phép tính độc lập khớp artifact về micro, số ghi chú còn FN, chỉ số từng nhãn và 15 ví dụ lỗi. Hash test, trọng số, nguồn rules và dịch vụ phân tích khớp metadata. Chạy lại runner cho cùng kết quả. [Artifact tiếng Việt](../artifacts/evaluation-vi.json)

| Chế độ | TP | FP | FN | Precision | Recall | Micro-F1 | Ghi chú có FN |
|---|---:|---:|---:|---:|---:|---:|---:|
| Rules | 1 | 8 | 32 | 11,11% | 3,03% | 4,76% | 15/20 |
| NER | 12 | 0 | 21 | 100,00% | 36,36% | 53,33% | 12/20 |
| Hybrid | 13 | 4 | 20 | 76,47% | 39,39% | 52,00% | 11/20 |

### Mục tiêu F1 ≥ 85% theo từng nhãn

| Nhãn | Support | Rules | NER | Hybrid |
|---|---:|---:|---:|---:|
| NAME | 17 | 0,00% | 69,23% | 69,23% |
| DOB | 4 | 0,00% | 0,00% | 0,00% |
| PHONE | 4 | 0,00% | 0,00% | 0,00% |
| ID | 5 | 33,33% | 0,00% | 33,33% |
| ADDR | 3 | 0,00% | **100,00%** | **100,00%** |

**Mục tiêu trên đủ năm nhãn chưa đạt.** Rules chưa đạt ngưỡng ở nhãn nào. NER và hybrid chỉ đạt ở ADDR, với 3/3 vùng vàng. NAME, DOB, PHONE và ID đều dưới ngưỡng ở cả ba chế độ. Cả ba micro-F1 cũng dưới 85%. Chỉ số này là tổng hợp của năm nhãn. Kết luận về quy trình G3 thuộc QA và Tech Lead.

NER CRF chỉ hỗ trợ NAME và ADDR. Trên bộ test này, hybrid giữ 12 TP của NER, thêm một ID đúng và thêm bốn PHONE sai. Số ghi chú có FN giảm từ 12 xuống 11, còn micro-F1 giảm từ 53,33% xuống 52,00%. Số mẫu ADDR nhỏ và toàn bộ dữ liệu là giả lập. [Phạm vi và ưu tiên các chế độ](engines.md)

### Ví dụ lỗi đã đối chiếu

- **Sai biên ADDR (`vi-test-012`, rules).** Gold `[37,83)` chỉ chứa giá trị địa chỉ. Dự đoán `[29,83)` thêm tiền tố `cư trú: `. Tuple dự đoán là một FP và tuple vàng là một FN.
- **Sai ngữ cảnh PHONE (`vi-test-005`, rules và hybrid).** Dự đoán `[40,50)` là số `0900000041`. Nguyên văn xác định đó là số lưu kho, nên không có vùng vàng PHONE tương ứng. Đây là một FP.
- **Sót NAME (`vi-test-002`, NER và hybrid).** Gold `[53,66)` là `bùi mộc nhiên`, tên người liên hệ viết thường. Cả hai chế độ thiếu vùng vàng này, tạo một FN NAME cho mỗi chế độ.

Trọng số CRF CPU có revision `sha256:8f0ee850c659b7c13d23280cad1a7c88c1fd051dc462ca5188810d392a7bce3f`. Cấu hình `lbfgs`, `c1=0.05`, `c2=0.1`, tối đa 100 vòng, được chọn trên validation. Dữ liệu và cấu hình khóa được giữ nguyên trong lần đối chiếu này. [Metadata mô hình](../artifacts/model/metadata.json)

```powershell
.\.venv\Scripts\python.exe -B -m ml.evaluate --output-dir artifacts/local/g3-ba
```

## Đối chứng tiếng Anh

Ba công cụ chạy đủ 16 ghi chú `en-g2-v1`. BA kiểm SHA-256 của corpus, ID và họ, phiên bản thực thi cùng hash lock. BA chạy lại ba worker và tính độc lập hợp các vị trí trên từng ghi chú. Tổng số vị trí vàng là 399 ở mọi lần chạy. TP/FP/FN, chỉ số, số ghi chú có FN và 18 ví dụ lỗi khớp artifact DevOps. [Artifact tiếng Anh](../artifacts/evaluation-en.json)

| Công cụ | TP | FP | FN | Precision | Recall | Micro-F1 | Ghi chú có FN |
|---|---:|---:|---:|---:|---:|---:|---:|
| Presidio | 267 | 237 | 132 | 52,98% | 66,92% | 59,14% | 9/16 |
| Philter UCSF | 341 | 132 | 58 | 72,09% | 85,46% | 78,21% | 12/16 |
| GEMINI pyDeid | 195 | 100 | 204 | 66,10% | 48,87% | 56,20% | 11/16 |

Philter có F1 vùng che cao nhất trong lần chạy này, nhưng vẫn có vị trí sót trên 12/16 ghi chú. Chỉ số vị trí và số ghi chú có FN cho thấy hai khía cạnh của độ phủ. Bảng tiếng Anh chấm vị trí trong vùng và không báo F1 từng nhãn. Mục tiêu theo nhãn ở trên áp dụng cho bài đo tiếng Việt.

- **Presidio Analyzer 2.2.366** dùng spaCy `en_core_web_sm` 3.7.1. Ở `en-001`, nhận cả từ dẫn `DOB` `[21,24)`, nằm ngoài các vùng vàng, nên ba vị trí tính FP.
- **Philter UCSF** dùng `philter_delta.json` tại revision đã pin, đọc UTF-8 và ánh xạ vị trí sau quy đổi xuống dòng về nguyên văn. Ở `en-001`, dấu `/` `[28,29)` trong ngày sinh vàng `[26,36)` còn nguyên, nên vị trí đó tính FN.
- **GEMINI pyDeid 1.0.1** chạy với `named_entity_recognition=False`. Ở `en-001`, che ngày khám `11/21/2026` `[83,93)`, nằm ngoài vùng ngày sinh vàng, nên mười vị trí tính FP.

Chạy lại với ba môi trường đã khóa theo [hướng dẫn upstream](upstream.md). Dùng đường dẫn riêng để lưu kết quả tái hiện.

```powershell
powershell.exe -NoProfile -File .\scripts\evaluate-upstream.ps1 -OutputPath artifacts/local/g3-ba/evaluation-en.json
```
