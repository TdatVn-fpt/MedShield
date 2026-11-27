# Thực nghiệm MedShield — G3

**READY_FOR_REVIEW.** BA đối chiếu nhãn vàng, dự đoán và artifact tiếng Việt, tiếng Anh. QA và Tech Lead rà soát báo cáo.

Phần G3 dưới đây ghi kết quả baseline đã kiểm tra ở commit `773cead6eea623a345e1e1fa6b5732a8b2b6ae77`. [Artifact so sánh Phase Q](../artifacts/phase-q-comparison.json) lưu baseline và bản Phase Q. [Artifact tổng hợp đang phục vụ API](../artifacts/evaluation.json) có ba kết quả tiếng Việt Q2 trên test gốc và ba kết quả tiếng Anh G3 giữ nguyên.

## Kết quả Phase Q

Trên test khóa gốc 20 ghi chú / 33 vùng vàng, micro-F1 Rules từ 4,76% lên 40,00%, CRF giữ 53,33% và Hybrid từ 52,00% lên 53,06%. Trên test mới 150 ghi chú / 560 vùng vàng, Rules từ 32,00% lên 70,69%, CRF giữ 46,35% và Hybrid từ 62,75% lên 81,45%. Cả hai dùng cùng scorer đã đóng băng. DOB và PHONE của Rules vẫn 0% trên test gốc, nên dừng trước Phase M. [Bảng từng nhãn, lệnh tái tạo và lỗi](phase-q.md)

Tập 150 ghi chú do agent sinh và gán nhãn chỉ dùng để phát hiện hồi quy. Điểm của tập này không dùng để ước tính khoảng cách đến cổng chất lượng. Các tuyên bố chất lượng sau Phase E phải dùng tập khóa độc lập và kèm strict F1, partial F1, khoảng tin cậy bootstrap theo ghi chú và tỉ lệ ghi chú còn sót vùng. [Quy trình Phase E](phase-e.md)

## Kết quả hồi quy Phase Q2

Hybrid trên test lịch sử đạt strict/partial F1 84,75%, CI 95% strict 70,18%–94,92%. Tỉ lệ ghi chú còn ký tự PHI ngoài vùng che là 25,00% (5/20), CI 10,00%–45,00%. Q2 khôi phục DOB, PHONE và ADDR trong phép đối chiếu hồi quy. Báo cáo tách số đúng dải/ngoài dải và liệt kê những lát còn yếu. Cổng chất lượng vẫn chờ tập độc lập Phase E. [Báo cáo hồi quy Q2](phase-q2.md)

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

Kết quả G3 `exact_span_label` trên 20 ghi chú test. BA đối chiếu lại 33 tuple vàng đã gán độc lập, khớp toàn bộ với nhãn QA. Sau đó gọi `/api/analyze` qua FastAPI TestClient cho 60 lượt ghi chú × chế độ. Phép tính độc lập khớp báo cáo baseline về micro, số ghi chú còn FN, chỉ số từng nhãn và 15 ví dụ lỗi. Hash test, trọng số, nguồn rules và dịch vụ phân tích khớp metadata baseline. [Kết quả lưu trong mục `sets.original.versions.before`](../artifacts/phase-q-comparison.json)

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

## Meddies-first trước huấn luyện

So từng ứng viên đánh giá với toàn bộ 22.310 ghi chú train tạm bằng Jaccard word 5-gram. Không loại ứng viên nào qua ngưỡng > 0,5 hoặc qua phép so tổ hợp tên và số điện thoại/ngày sinh. 299 ghi chú còn lại chia thành validation 149 và test 150 theo loại tài liệu. p50 độ dài ứng viên là 362 code point, trong khi train là 1.156. Giới hạn là “tách tập bằng cô lập nguồn sinh + khử trùng trùng lặp gần giống; phân nhóm bệnh nhân/họ mẫu không kiểm chứng được từ metadata công khai của nhà phát hành”. Gói đang gán, chưa có kết quả IAA, tập silver-locked hoặc điểm Phase M. [Bảng phân bố và manifest](../artifacts/meddies-step3-dedup.json) · [Giao thức](meddies-silver.md)

### Nguồn checkpoint và kiểm tra tách từ trước Phase M

Đối chiếu revision và SHA-256 do kho upstream công bố. Các revision ứng viên dưới đây đều có trước Meddies PII v2. Tài liệu công khai mô tả corpus tiền huấn luyện nhưng không cung cấp danh mục từng văn bản. Lịch sử revision là bằng chứng về tuổi của checkpoint. Chưa nạp trọng số, fine-tune hoặc chọn mô hình.

| Ứng viên | Revision | Tệp trọng số và SHA-256 do upstream công bố |
|---|---|---|
| PhoBERT-large | `1c7880f20db59c0054c6de5afd71b012369f6ee4` (2024) | `pytorch_model.bin`, `4be3329449abd3a6865d7936625f1474187b15b59a67c2fecb5a639226a94d6f`. [Checkpoint MIT](https://huggingface.co/vinai/phobert-large/tree/1c7880f20db59c0054c6de5afd71b012369f6ee4) · [Bài báo tiền huấn luyện Wikipedia và tin tức](https://aclanthology.org/2020.findings-emnlp.92/) |
| ViHealthBERT-word | `f89e80b461e86f9cfc1c84019bd819830c24b6c5` (2022) | `pytorch_model.bin`, `3259d96cb56cb1c85b0a5a894e782a6a4ee66d783333d83368fba36d23be2d06`. Nhóm tác giả trỏ tới đúng bản word-level. Kho mã có MIT. Kho trọng số chưa khai báo riêng giấy phép nên phạm vi dùng và phát hành trọng số vẫn cần xác nhận. [Kho của tác giả](https://github.com/demdecuong/vihealthbert) · [Checkpoint tác giả công bố](https://huggingface.co/demdecuong/vihealthbert-base-word/tree/f89e80b461e86f9cfc1c84019bd819830c24b6c5) · [Bài báo](https://aclanthology.org/2022.lrec-1.35/) |
| XLM-R-large | `c23d21b0620b635a76227c604d44e43a9f0ee389` (2024) | `model.safetensors`, `2dfa19f172412917cab174da04b46e2134811b723666965fd0aabd97caa6e23b`. [Checkpoint MIT](https://huggingface.co/FacebookAI/xlm-roberta-large/tree/c23d21b0620b635a76227c604d44e43a9f0ee389) · [Bài báo tiền huấn luyện CommonCrawl đa ngữ](https://aclanthology.org/2020.acl-main.747/) |

Loại checkpoint Meddies PII v2 khỏi nhóm ứng viên cho phép đo độc lập vì nhà phát hành khai báo đã huấn luyện trên nguồn Meddies PII v2. [Model card của nhà phát hành](https://huggingface.co/Meddies/meddies-pii-v2#how-we-trained-the-model)

Smoke trên Java 17.0.9 và VnCoreNLP 1.2 đã chạy được `wseg` bằng fixture tự tạo. Đã đối chiếu 18 token về vị trí code point trên nguyên văn. Đầu ra ghép `Mai_An`, giữ dạng tổ hợp Unicode trong tên khác và có thể giữ dấu chấm trong token như `A.`. Triển khai word-level cần duy trì ánh xạ này qua tách từ và subword, kể cả khoảng trắng, CRLF, emoji, dấu tổ hợp và dấu câu. Fixture và đầu ra chỉ lưu cục bộ ở `artifacts/local/meddies/phase-m-preflight/`.

```powershell
Set-Location artifacts/local/meddies/phase-m-preflight
java '-Xmx1g' '-Dfile.encoding=UTF-8' -jar VnCoreNLP-1.2.jar -fin synthetic-smoke.txt -fout synthetic-out.txt -annotators wseg
```

### Kiểm trùng train giả lập MedShield với hai gói Meddies

Kiểm tra chuẩn bị trước Phase M, chỉ dùng văn bản chưa gán nhãn. Nạp 60 ghi chú train MedShield từ `data/train.jsonl` bằng `ml.dataset.load_dataset`, SHA-256 `5de2c3087d01b0ef69d048a20682703cb8672c6b6869d05f3c10b9332ff1fad3`. So nguyên văn và tính Jaccard chính xác theo cùng phương pháp word 5-gram của Bước 3 trên từng cặp train với hai gói gán mù đã ghim.

| Gói so | Số cặp | Trùng nguyên văn | Ghi chú train vượt 0,5 | Jaccard lớn nhất |
|---|---:|---:|---:|---:|
| Validation | 8.940 | 0 | 0 | 0 |
| Test | 9.000 | 0 | 0 | 0 |

Dùng lệnh dưới đây từ thư mục repo để tái tạo thống kê. SHA-256 của từng gói phải khớp [manifest Bước 3](../artifacts/meddies-step3-dedup.json). Dò thêm tổ hợp NAME + PHONE hoặc NAME + DOB từ nhãn của 60 ghi chú train cũng cho 0 ghi chú khớp ở cả hai gói. Kết quả chỉ áp dụng cho đúng byte của các tệp đã so, và cần đối chiếu lại sau khi khóa tập và sau khi chuẩn bị dữ liệu tăng cường.

```powershell
@'
from hashlib import sha256
from pathlib import Path
from ml.dataset import load_dataset
from ml.meddies_overlap import SurfaceIndex, max_similarity, shingles, surface_keys, words
from ml.meddies_silver import packet_rows

train = load_dataset(Path("data")).train
grams = [shingles(words(note.text), 5) for note in train]
surface = SurfaceIndex()
for note in train:
    names, values = set(), set()
    for span in note.entities:
        value = note.text[span.start:span.end]
        if span.label == "NAME":
            name = tuple(words(value))
            if name:
                names.add(name)
        elif span.label in {"PHONE", "DOB"}:
            values.update((span.label, key) for key in surface_keys(value, span.label))
    surface.add(names, values)
root = Path("artifacts/local/meddies/step3-source-isolated")
for split in ("validation", "test"):
    packet = (root / f"{split}-blind.jsonl").read_bytes()
    withheld = set(packet_rows(packet).values())
    hits = max_similarity(grams, withheld)
    print(split, sha256(packet).hexdigest(), len(train) * len(withheld),
          sum(note.text in withheld for note in train), sum(score > 0.5 for score in hits),
          max(hits), sum(bool(surface.matches(text)) for text in withheld))
'@ | uv run --locked python -X utf8 -
```
