# Phase M · Nguồn checkpoint và chạy thử phía train

Ngày 27/11/2026. Trạng thái chuẩn bị. Đã thử môi trường, tách từ và mã hóa BIO với tokenizer ghim. Lượt fine-tune sẽ chạy sau khi gửi gói phân xử.

## Checkpoint giữ cho bake-off

| Checkpoint | Revision trên Hugging Face | Đầu vào | Nguồn tiền huấn luyện do tác giả công bố |
| --- | --- | --- | --- |
| `vinai/phobert-large` | `70e2cfcd3cce29c970aee4954ea34a32bb30afdc` | Tiếng Việt đã tách từ, tối đa 256 token | Wikipedia và tin tức tiếng Việt, 20 GB. [VinAI](https://github.com/VinAIResearch/PhoBERT) · [Checkpoint](https://huggingface.co/vinai/phobert-large/tree/70e2cfcd3cce29c970aee4954ea34a32bb30afdc) |
| `demdecuong/vihealthbert-base-word` | `f89e80b461e86f9cfc1c84019bd819830c24b6c5` | Tiếng Việt đã tách từ, tối đa 256 token | Văn bản tiếng Việt miền y tế. [Bài báo LREC](https://aclanthology.org/2022.lrec-1.35/) · [Checkpoint](https://huggingface.co/demdecuong/vihealthbert-base-word/tree/f89e80b461e86f9cfc1c84019bd819830c24b6c5) |
| `FacebookAI/xlm-roberta-large` | `c23d21b0620b635a76227c604d44e43a9f0ee389` | Văn bản gốc, SentencePiece, tối đa 512 token | Common Crawl đã lọc cho 100 ngôn ngữ. [Bài báo ACL](https://aclanthology.org/2020.acl-main.747/) · [Checkpoint](https://huggingface.co/FacebookAI/xlm-roberta-large/tree/c23d21b0620b635a76227c604d44e43a9f0ee389) |

Đã đọc API `huggingface.co/api/models/<repo>` để lấy revision và đối chiếu `config.json` tại từng revision. Cả ba là bản tiền huấn luyện gốc. PhoBERT-large và XLM-R-large ghi MIT. Kho nghiên cứu ViHealthBERT ghi MIT, metadata của checkpoint không ghi giấy phép trọng số riêng. Lưu ViHealthBERT cục bộ cho thử nghiệm và để trọng số ngoài gói bàn giao. [Kho nghiên cứu ViHealthBERT](https://github.com/demdecuong/vihealthbert) · [Thẻ checkpoint ViHealthBERT](https://huggingface.co/demdecuong/vihealthbert-base-word)

Các mô tả và mốc công bố không cho thấy ba checkpoint gốc được huấn luyện trên Meddies. Đây là suy luận từ nguồn công bố và lịch sử checkpoint. Chưa đối chiếu được từng dòng tiền huấn luyện. Khi tải sẽ lưu hash trọng số thực tế và giữ đúng revision. Phạm vi tuyên bố cho Meddies là benchmark synthetic độc lập, học thuật theo giao thức đã đăng ký.

## Chạy thử cục bộ sau khi gửi gói phân xử

Chạy trước với ViHealthBERT bản word, 135 triệu tham số, để đo được chi phí CPU và kiểm đường đi từ vùng gán đến mô hình. Máy Windows có Intel Core i7-10850H, 6 lõi/12 luồng, khoảng 31,7 GiB RAM và Intel UHD Graphics. Không gian chạy thử dùng train đã ánh xạ lại và validation nội bộ cắt từ chính train, có seed và manifest riêng. Số liệu ghi **validation nội bộ phía train, không dùng tuyên bố**. [Thông số ViHealthBERT](https://github.com/demdecuong/vihealthbert)

PhoBERT và ViHealthBERT đều khuyến nghị RDRSegmenter. Chuẩn bị dùng bản VnCoreNLP 1.2 đã có smoke trên fixture giả lập. Đầu vào mô hình có thể được tách từ trên bản sao. Vùng kết quả phải quy chiếu về code point của văn bản gốc, gồm Unicode tổ hợp và span qua nhiều token. Dùng cửa sổ chồng nhau cho ghi chú dài và báo vùng train không khớp biên token. JAR và các tệp từ điển giữ cục bộ, có hash trước khi dùng. [Hướng dẫn PhoBERT](https://github.com/VinAIResearch/PhoBERT#notes) · [Hướng dẫn ViHealthBERT](https://huggingface.co/demdecuong/vihealthbert-base-word#example-usage-for-raw-text) · [VnCoreNLP](https://github.com/vncorenlp/VnCoreNLP)

Đo một vòng ngắn có cập nhật trọng số, ghi thời gian, thông lượng, RAM và seed. Nếu chi phí full fine-tune vượt khả năng máy, so sánh khả năng chạy LoRA dùng cấu hình chung cho các mô hình và đo lại chi phí trước khi chốt siêu tham số. Giữ cả biến thể có và không CRF của từng checkpoint cho bake-off sau khi khóa silver. Chỉ dùng validation đã khóa để chọn mô hình và hiệu chuẩn. Test đã khóa được mở một lần sau khi cấu hình đã đóng băng. [Tài liệu PEFT chính thức](https://huggingface.co/docs/transformers/peft)

## Bằng chứng chuẩn bị Phase M.1

- `torch 2.10.0+cpu` và `transformers 4.57.3` import thành công trong môi trường chạy thử riêng. `torch.cuda.is_available()` trả về `False`. Phương án chạy thử là AdamW trên CPU, với tham số ban đầu 6 luồng, 16 lần cập nhật, batch 2 và learning rate `2e-5`. Chốt cấu hình bake-off sau khi có thời gian và số đo từ lượt cập nhật thực. [PyTorch AdamW](https://docs.pytorch.org/docs/2.10/generated/torch.optim.AdamW.html) · [Transformers token classification](https://huggingface.co/docs/transformers/v4.57.3/tasks/token_classification)
- Chia 64 ghi chú fit và 24 ghi chú validation nội bộ từ bản train v3, seed `20261127`, không trùng mã giữa hai tập. RDRSegmenter và tokenizer ViHealthBERT ghim tạo được 119 cửa sổ từ 60/64 ghi chú fit và 41 cửa sổ từ 21/24 ghi chú validation nội bộ, mỗi cửa sổ tối đa 256 token. Các vùng validation thiếu ánh xạ vẫn thuộc mẫu số chấm strict. Các số liệu trên mô tả đường ống của benchmark synthetic độc lập, học thuật.
- Đã tải `config.json`, `bpe.codes` và `vocab.txt` tại revision ViHealthBERT đã ghi. `pytorch_model.bin` có SHA-256 LFS `3259d96cb56cb1c85b0a5a894e782a6a4ee66d783333d83368fba36d23be2d06` theo metadata ghim. Tệp trọng số sẽ được kiểm hash trước khi nạp. [Metadata revision](https://huggingface.co/api/models/demdecuong/vihealthbert-base-word/revision/f89e80b461e86f9cfc1c84019bd819830c24b6c5?blobs=true)

Lệnh chạy thử sau khi gửi gói phân xử:

```powershell
$meddies = 'artifacts/local/meddies'
$pilot = "$meddies/phase-m-preflight"
uv run --locked --with 'torch==2.10.0' --with 'transformers==4.57.3' python -X utf8 -m ml.meddies_m_preflight "$meddies/step4-remapped-v3/provisional-train.jsonl" artifacts/meddies-step4-remapped.json $pilot "$pilot/vihealthbert-cpu-pilot.json"
```
