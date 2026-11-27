# Meddies-first — Kết quả Bước 1 và Bước 2

Nguồn được chủ dự án duyệt cho học thuật phi thương mại. Shard tiếng Việt lấy đúng commit `5dbe7cde649446028f628820c204bf53bb296894`, 43.345.758 byte, SHA-256 `331640296be10a56a468e1cf9d5014dc9d1de13ab304b9294df0643b2ddbc04a`. Bản raw và các trích đoạn train giữ trong `artifacts/local/meddies/`. [Dataset card đã ghim](https://huggingface.co/datasets/Meddies/meddies-pii-v2/blob/5dbe7cde649446028f628820c204bf53bb296894/README.md) · [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)

## Bước 1 — QA nguồn

1. **Thực hiện.** `ml/meddies_qa.py` kiểm SHA-256, đọc nguyên văn và metadata, không dùng cột nhãn. Lọc cả hai trường miền y tế, ngôn ngữ, nguồn sinh và danh sách loại tài liệu lâm sàng/hành chính đã khai báo. Cô lập một nguồn sinh khác cho ứng viên đánh giá. Loại trùng nguyên văn giữa hai nhóm và trong nhóm trước khi đếm.
2. **Số liệu.** Có 38.963 dòng nguồn, 31.346 dòng mang profile y tế. Bộ lọc chặt thu được **22.310 dòng train tạm** và **299 ứng viên đánh giá**; không có bản trùng nguyên văn trong hai nhóm đã lọc. Độ dài train p50/p95 1.156/2.283 code point; ứng viên đánh giá 362/420. Đủ ngưỡng số lượng ≥2.000 và ≥200. Toàn bộ phân bố theo loại ghi chú ở [manifest QA](../artifacts/meddies-step1-qa.json).
3. **Nguyên nhân loại.** Loại 7.617 dòng ngoài miền y tế và 8.737 dòng mang profile y tế nhưng thiếu metadata hoặc nằm ngoài nguồn/loại tài liệu cho phép. Trong shard đầy đủ có cả văn bản kỹ thuật mang nhãn miền y tế, nên không dùng riêng `domain_profile` để nhận hồ sơ.
4. **Kiểm tra.** Chạy `uv run --locked --with pyarrow==20.0.0 python -X utf8 -m ml.meddies_qa artifacts/local/meddies/vietnamese.parquet --output artifacts/local/meddies/qa-recheck.json`. Kiểm thử thêm trường hợp văn bản trùng giữa hai nhóm.
5. **Rủi ro.** Ứng viên đánh giá có 299 `original_id` khác nhau và cùng một `scenario`, `source`, `source_dataset` và profile. Train tạm không có `original_id`, có sáu scenario và 13 nguồn sinh. Các trường đó cho biết nguồn tạo hoặc mô tả tài liệu nhưng chưa đủ chứng minh nhóm bệnh nhân hay họ mẫu. Hai endpoint metadata của nguồn sinh con trả HTTP 401 khi truy cập công khai, chưa cung cấp bằng chứng bổ sung. Không biến mã dòng thành mã bệnh nhân.
6. **Quyết định.** Đủ số lượng để ánh xạ train tạm. Bước 3 cần bằng chứng truy vết nhóm cho các dòng được nhận hoặc phương án nguồn độc lập thay thế. Giữ nguyên cổng tách nhóm của Phase E.

## Bước 2 — Ánh xạ nhãn train tạm

1. **Thực hiện.** `ml/meddies_train.py` dùng đúng bộ lọc Bước 1. `human_name`, `phone_number`, `address` và `id_number` lần lượt ánh xạ sang NAME, PHONE, ADDR và ID. `date` chỉ thành DOB nếu có neo trong ngữ cảnh được định nghĩa ở [hướng dẫn gán nhãn](annotation-guide.md). Kiểm offset và chuỗi gốc bằng code point, loại nhóm ngoài phạm vi. Không ánh xạ các nhãn của 299 ứng viên đánh giá.
2. **Số liệu.** Trên 22.310 dòng, giữ 178.233/369.375 vùng; loại 51,75%. Giữ 7.474/44.683 DATE thành DOB (16,73%). [Manifest ánh xạ](../artifacts/meddies-step2-mapping.json)

   | Nhãn | Trước ánh xạ | Sau ánh xạ |
   |---|---:|---:|
   | NAME | 45.978 | 45.978 |
   | PHONE | 39.222 | 39.222 |
   | ADDR | 29.174 | 29.173 |
   | ID | 56.386 | 56.386 |
   | DOB (nguồn DATE) | 44.683 | 7.474 |

3. **Nguyên nhân loại.** 153.932 vùng thuộc nhãn ngoài phạm vi, 37.209 DATE thiếu neo DOB, 1 ADDR không khớp offset/giá trị. Mẫu soát 20 vùng ngẫu nhiên mỗi nhãn được tạo với seed 20261126 trong `artifacts/local/meddies/step2-reviewed/train-mapping-samples.json`; chưa có người soát. Không công bố ví dụ trích văn bản trong báo cáo tổng hợp.
4. **Kiểm tra.** Tái tạo bản lịch sử bằng `uv run --locked --with pyarrow==20.0.0 python -X utf8 -m ml.meddies_train artifacts/local/meddies/vietnamese.parquet --legacy-mapping --private-output artifacts/local/meddies/step2-recheck --output artifacts/local/meddies/mapping-recheck.json`. Hai lượt ghi cùng hash train tạm. Test bao phủ neo DOB, Unicode, loại ngày khám, vùng ngoài phạm vi, biên sai và vùng chồng lấn.
5. **Rủi ro.** Nhãn tự động chỉ là dữ liệu train tạm, chưa có đánh giá độ chính xác ánh xạ bằng người. Cần kiểm trùng họ và bệnh nhân trước khi giữ lại dữ liệu train thật sự. Chưa chia validation/test, chưa chạy train, chưa đo IAA hoặc điểm chất lượng.
6. **Quyết định.** Bản yêu cầu vẫn để trống người A, B và trọng tài. Cần chủ dự án chỉ định ba vai trò, đồng thời cho biết đầu mối/bằng chứng nhóm Meddies hoặc chốt nguồn thay thế nếu không thể xác minh. Chưa chọn phương án người–LLM.

## Bước 3 — Giao thức khử trùng đã được duyệt

Ngày 26/11/2026, chủ dự án chấp thuận thay sổ nhóm bằng cô lập nguồn sinh và khử trùng. Chủ dự án là người gán chính kiêm phân xử. Lượt hai độc lập dùng LLM ngoài họ GPT trên cùng gói văn bản. [Kết quả Bước 3, cách gán và cổng giữ nguyên](meddies-silver.md)

### Phương án sổ nhóm trước quyết định

QA giữ bằng chứng nhóm do nhà phát hành hoặc người kiểm chứng độc lập cung cấp. Chỉ lập sổ nhóm cho ghi chú có chứng cứ về cả bệnh nhân lẫn họ mẫu. Sổ có các trường `schema_version: 1`, `revision`, `shard_sha256`, `evidence_sha256` và mã `reviewer`. Mỗi dòng trong mảng `rows` có `note_id`, `text_sha256` của chuỗi UTF-8 nguyên văn, `patient_group`, `family_id`, `split`, `slices` và mã tham chiếu `evidence_ref`. QA đối chiếu mã tham chiếu với nội dung bằng chứng riêng. Với train, `slices` rỗng. Với validation/test, lát được khai báo trước khi gán. Người giữ sổ không dùng `original_id`, chỉ số dòng hay tên loại văn bản thay cho bằng chứng nhóm.

```powershell
$meddies = 'artifacts/local/meddies'
uv run --locked --with pyarrow==20.0.0 python -X utf8 -m ml.meddies_split "$meddies/vietnamese.parquet" "$meddies/group-ledger.json" "$meddies/group-evidence.json" "$meddies/step3"
```

Lệnh chỉ đọc văn bản và metadata từ shard. Nó kiểm hash văn bản và bằng chứng, từ chối trùng bệnh nhân/họ hoặc nguyên văn, và giữ nguyên giới hạn test 150–200 ghi chú, tổng validation/test ít nhất 200 ứng viên cùng tối thiểu 2.000 ghi chú train có bằng chứng. Một bản văn bản đã dành cho nhóm ứng viên luôn bị loại khỏi train, kể cả khi chưa được nhận vào validation/test. Đầu ra cục bộ có `train-membership.jsonl` (mã ghi chú thuộc train, không có nhãn), `train-groups.jsonl`, `validation-source.jsonl`, `source.jsonl` (nguồn test) và manifest hash. Người gán dùng hai tệp nguồn đánh giá với [luồng gán mù Phase E](phase-e.md). Cần kiểm support thật, IAA và phân xử trước khi khóa. Chưa có sổ nhóm đã duyệt để chạy trên shard thật.

Đã đối chiếu thêm [preprint của nhóm Meddies, mục 3 và phụ lục B](https://arxiv.org/html/2611.29491v1). Tác giả mô tả `scenario` là ngữ cảnh sinh và yêu cầu về nhãn. Tài liệu nhắc đến nhóm mẫu lâm sàng bổ sung nhưng không công bố bảng ánh xạ từ ID dòng shard đã ghim sang bệnh nhân giả lập và họ mẫu. Bằng chứng cần ở đây là bảng ánh xạ cho các dòng sẽ dùng, hoặc tài liệu từ nhà phát hành xác nhận các cohort tách biệt và cách nhận diện bệnh nhân/họ trong từng cohort. Bảng chỉ cần dùng mã vô danh, không cần chia sẻ văn bản hoặc giá trị định danh.

## Bước 4 — Tiếp nhận phiếu rà soát ánh xạ train

Chủ dự án duyệt phiếu ngày 27/11/2026. Bản đính kèm và `artifacts/local/meddies/step4/mapping-review.csv` trùng từng byte, SHA-256 `f27c56d34aae804a3827278bf37eaf7036ce3fc906d54b28d076dd2b0903340e`. Đối chiếu đủ 100 dòng theo nhãn, số mẫu, mã ghi chú và giá trị với mẫu Bước 2 có SHA-256 `f5d47d6a0dc09e43b47749a7310bf54c85253d3478c5b9051bf8fc53e0e69edf`.

Có 80 dòng `ok` và 20 dòng `needs_correction` có lý do. Số mẫu cần sửa gồm 5 NAME, 9 ADDR và 6 ID. DOB và PHONE đều có 20/20 mẫu `ok`. Kết quả này mô tả phiếu rà soát 100 vùng của tập train tạm trên benchmark synthetic độc lập, học thuật.

Chủ dự án chốt bỏ mã đơn/phiếu khỏi ID, bỏ địa chỉ cơ sở y tế và IP khỏi ADDR. Đồng thời cắt danh xưng khỏi NAME, loại khoảng tham chiếu xét nghiệm khỏi ID, cắt nhãn trường và xử lý nhất quán neo `BHYT-`. Áp dụng trên toàn bộ 22.310 ghi chú train và giữ bộ lọc DOB, PHONE.

### Ánh xạ lại toàn bộ train

1. **Đã làm.** Áp dụng chính sách đã duyệt lên toàn bộ 22.310 ghi chú train tạm. Bộ ánh xạ chỉ giữ biên code point từ nguyên văn và thu hẹp hoặc bỏ các vùng có ngữ cảnh phù hợp. `BHYT-` ở đầu vùng được cắt như neo, còn giá trị phía sau giữ nguyên. Các trường định danh đơn và khoảng tham chiếu có dạng HL7 được nhận biết dựa trên vị trí trường đã công bố. [HL7 v2.8.2, chương 7](https://hl7.eu/HL7v2x/v282/std282/ch07.html)
2. **Bằng chứng.** Đã chạy lệnh dưới đây với thư mục đầu ra mới. SHA-256 bản train cục bộ là `b943bf1f039cd01a19486aa89dd543c50d9e75f7a60565f7bfe2e75022af631b`. SHA-256 báo cáo tổng hợp là `b3f565aaa37dea425b7fc731d364afdb25e953021105247d521f8223cacec9f3`. Đối chiếu train trước/sau trong `meddies-step4-remap-v3-verification.json` thuộc thư mục dữ liệu cục bộ. [Báo cáo tổng hợp](../artifacts/meddies-step4-remapped.json)

   ```powershell
   $meddies = 'artifacts/local/meddies'
   uv run --locked --with pyarrow==20.0.0 python -X utf8 -m ml.meddies_train "$meddies/vietnamese.parquet" --private-output "$meddies/step4-remapped-v3" --output "$meddies/meddies-step4-remapped-v3.json"
   ```

3. **Số liệu.** Số đếm toàn bộ tập train của benchmark synthetic độc lập, học thuật. Bảng thống kê số vùng, không ước lượng chất lượng mô hình hay khoảng tin cậy.

   | Nhãn | Ánh xạ cũ | Ánh xạ lại | Chênh lệch |
   | --- | ---: | ---: | ---: |
   | NAME | 45.978 | 45.971 | −7 |
   | DOB | 7.474 | 7.474 | 0 |
   | PHONE | 39.222 | 39.222 | 0 |
   | ID | 56.386 | 51.327 | −5.059 |
   | ADDR | 29.173 | 23.867 | −5.306 |
   | **Tổng** | **178.233** | **167.861** | **−10.372** |

   | Quy tắc | Tác động | Số vùng |
   | --- | --- | ---: |
   | NAME có tên sau danh xưng | Cắt danh xưng | 6.960 |
   | NAME chỉ có danh xưng | Loại | 7 |
   | ADDR là địa chỉ cơ sở y tế | Loại | 5.094 |
   | ADDR là IP | Loại | 212 |
   | ID là mã gắn với đơn/phiếu | Loại | 4.144 |
   | ID là khoảng tham chiếu xét nghiệm | Loại | 373 |
   | ID là mã phi cá nhân khác | Loại | 542 |
   | ID chứa nhãn trường | Cắt nhãn trường | 556 |
   | ID có neo `BHYT-` ở đầu | Cắt neo | 2.043 |
   | ID chỉ có nhãn trường | Loại | 0 |

   Có 11.540 ghi chú thay đổi. Cắt biên 6.960 vùng NAME và 2.589 vùng ID phân biệt. Trong số đó có 10 vùng ID được cắt cả nhãn trường lẫn neo. Chênh lệch tổng chỉ đếm vùng bị loại.

4. **Đối chiếu.** Cả 22.310 ghi chú giữ đúng mã, nguyên văn và từng vùng DOB/PHONE. 80 vùng `ok` giữ nguyên, 20 vùng được đánh dấu sửa đã được xử lý. QA tái chạy từ shard đã ghim và kết luận PASS cho ánh xạ v3 khi các hash đầu ra khớp. Cổng IAA và chất lượng Phase M được đánh giá ở các bước riêng. [Biên bản độc lập](reviews/meddies-train-remap.md)
5. **Giới hạn.** Phiếu người duyệt có 100 mẫu từ bản cũ. Các luật dựa vào ngữ cảnh văn bản, nên vẫn có thể gặp mẫu ngoài ngữ cảnh đã rà. 4.171 vùng trong 1.639 ghi chú có khoảng trắng ở rìa kế thừa từ bản cũ. Bộ đọc Phase M xử lý khoảng trắng ở bản dùng để mã hóa BIO, giữ nguyên tệp ánh xạ và nguyên văn nguồn. Báo cáo mapper xác nhận phạm vi là train tạm và chưa chạy huấn luyện.
6. **Tiếp theo.** Dùng bản v3 cho đường ống Phase M. Giữ nguyên artifact Bước 2 mà manifest khử trùng đã ghim.
