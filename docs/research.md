# Nghiên cứu và quyết định kỹ thuật

Ngày kiểm tra: 18/11/2026, Asia/Saigon. Tác giả: Research/ML. Trạng thái G0: READY_FOR_REVIEW cho điều tra nguồn/phụ thuộc; **chưa có kết quả engine hay số liệu phiên bản mới**. Dev/QA review, chỉ triển khai G2 sau G1 PASS.

## Đầu vào đã đọc

- `C:\Users\Admin\Downloads\Presidio vs Philter vs PyDeID.html`: tài liệu nghiên cứu ngày 17/11/2026 do người dùng cung cấp. Dùng để định hướng, kiểm tra lại thông tin cài đặt từ source upstream.
- `C:\Users\Admin\Downloads\MedShield_SIC_Research.zip`: đọc Markdown nghiên cứu, đối chiếu slide SIC, lộ trình, dữ liệu và API; có `MedShield_Demo.html`. Không đưa ZIP hay toàn bộ slide khóa học vào repo.
- Bảng đối chiếu slide trong ZIP là tài liệu thứ cấp đã có; chưa tự mở bản slide gốc. Mốc được ghi trong đó: NLP chương 7 trang 14–16/33/47; Machine Learning 1 slide 173–182 về Precision/Recall/F-score. Không tuyên bố đã kiểm chứng các trang gốc.
- Demo cũ dùng perceptron học NAME và quy tắc cho nhãn khác. Điểm 94,7% trên 6 đoạn là **demo cũ, 6 đoạn**, không phải benchmark của bản mới.

## Nguồn, kết luận và việc phải kiểm chứng bằng code

| Nguồn chính thức | Kết luận dùng trong thiết kế | Kiểm chứng cần có ở G2–G3 |
|---|---|---|
| [Presidio source](https://github.com/data-privacy-stack/presidio/tree/9fc7774ed74faa0afd5ffb36da63e77b9a2f8c30) | Analyzer trả spans; Anonymizer riêng. Package source `presidio_analyzer` 2.2.366; Python >=3.11,<3.15; MIT. NLP engine/recognizer có thể tùy biến. | Import/cài thật, model tiếng Anh nếu dùng, chạy cùng văn bản gốc với hai engine khác; ghi rõ bộ recognizer và mapping, không coi DATE_TIME là DOB vô điều kiện. |
| [Philter source](https://github.com/BCHSI/philter-ucsf/tree/4da3cf31c9bfbfd66c66b141c45ba7a47628dd0a) | CLI tiếng Anh lâm sàng, blacklist/whitelist/regex/POS. LICENSE là BSD-3-Clause. README khuyên source. `Philter(config).map_coordinates(); transform()` tạo vùng che. | Môi trường riêng; requirements gốc `numpy==1.22.0`, `pandas==1.0.5` không phù hợp Python 3.12. Nếu dùng phiên bản tương thích mới phải ghi rõ thay đổi môi trường và smoke. Chấm vùng che nếu không có nhãn tương đương. |
| [GEMINI pyDeid source](https://github.com/GEMINI-Medicine/pyDeid/tree/f93d2ddb1fd857236b2d3b4b761af2b8028c7281) | `setup.py` xác nhận package `pyDeid` 1.0.1, MIT trong LICENSE.md. `deid_string(note, named_entity_recognition=False)` trả danh sách surrogate và chuỗi mới; trường `phi_start/phi_end/types` cho offsets gốc. | Cài **đúng URL+SHA GEMINI**; không cài theo tên PyPI chưa xác minh. Không lưu trường `phi`/surrogate map từ input người dùng. Mặc định là quy tắc/wordlist; NER spaCy là tùy chọn riêng. |
| [sklearn-crfsuite tutorial](https://sklearn-crfsuite.readthedocs.io/en/latest/tutorial.html), [source](https://github.com/scrapinghub/sklearn-crfsuite) | CRF học chuỗi nhãn BIO từ đặc trưng token và ngữ cảnh. Chạy CPU, không cần tải trọng số pretrained. Đây là mô hình học có giám sát thực sự, khác regex. | Train từ train, chọn cấu hình trên validation; QA giữ test. Lưu seed/config/hash dữ liệu/trọng số; chạy lại cùng exact-span+label scorer. |
| [Three.js cleanup chính thức](https://github.com/mrdoob/three.js/blob/dev/manual/en/cleanup.html), [responsive](https://github.com/mrdoob/three.js/blob/dev/manual/en/responsive.html) | Scene chỉ hỗ trợ giải thích phiếu khám giả lập. Lazy-load riêng; dispose geometry/material/texture/renderer khi unmount. | G4 thử WebGL unavailable, reduced-motion, 390/1440px. Thất bại 3D không được làm hỏng luồng rà soát. URL website manual `/manual/en/cleanup.html` từng fetch 404 trong phiên; source repo là fallback. |

SHA được lấy bằng `git ls-remote <repo> HEAD`, sau đó clone/read source ngoài repo tại `D:\Workspace\MedShield-upstream\`. Không phân phối clone cùng bài nộp. Ba công cụ hướng tiếng Anh hoặc cần cấu hình ngôn ngữ riêng; nghiên cứu hiện tại không chứng minh hỗ trợ NER y tế tiếng Việt sẵn. Không dùng số công bố trên corpus khác làm kết quả MedShield.

## Thiết kế thực nghiệm chính dự kiến

1. Rules: xét ngữ cảnh DOB/PHONE/ID; bổ sung NAME/ADDR theo tiền tố rõ nếu thiết kế baseline yêu cầu. Không lấy mọi ngày làm DOB.
2. NER: CRF BIO học từ ghi chú giả lập tiếng Việt. Ưu tiên NAME/ADDR; nếu huấn luyện cả năm nhãn thì công bố rõ. Không gọi quy tắc là NER.
3. Hybrid: chạy rules và CRF độc lập trên **cùng chuỗi gốc**, gộp spans rồi giải quyết chồng lấn có quy tắc đã khóa trên validation, giữ nguồn. Không nối các bản đã che qua nhiều engine.

Mục tiêu khoảng 100 ghi chú, mỗi ghi chú là một mẫu. Chia theo họ câu **trước** sinh biến thể; gồm mẫu không PHI, ghi chú tự do, chữ thường, địa chỉ nhiều phần, ngày hẹn/ICD/số đo và Unicode. Không dùng 6 ví dụ cũ làm test độc lập. Ghi riêng số người học tự rà soát; tại lúc viết chưa có bằng chứng người học đã rà soát mẫu mới, không được ghi số khác 0.

Đánh giá `(document_id,start,end,label)` exact match, trước sửa tay: TP/FP/FN/support theo nhãn, precision/recall/F1, micro-F1, số ghi chú còn ít nhất một FN. Trường hợp thiếu support phải thể hiện; ngưỡng >=85% được đối chiếu theo nhãn. Quy trình đánh giá có thể PASS dù mục tiêu chất lượng chưa đạt.

## Đối chứng tiếng Anh và chuẩn hóa

Presidio, Philter, GEMINI pyDeid phải chạy độc lập cùng text giả lập. Đối chứng vùng che có thể dùng tập vị trí ký tự không phải whitespace được engine che và tập vàng cùng đơn vị; báo riêng với exact span+label tiếng Việt. Không đưa điểm vùng che và điểm thực thể vào cùng cột để xếp hạng. DATE/DATE_TIME không tự đổi thành DOB nếu thiếu ngữ cảnh; vùng không phân loại tương đương được giữ là coverage.

## Lệnh cài/smoke dự kiến (chưa phải bằng chứng PASS)

```powershell
uv venv --python 3.12 .venv-upstream
uv pip install --python .venv-upstream/Scripts/python.exe presidio-analyzer==2.2.366
uv pip install --python .venv-upstream/Scripts/python.exe 'git+https://github.com/GEMINI-Medicine/pyDeid.git@f93d2ddb1fd857236b2d3b4b761af2b8028c7281'
# Philter source ở SHA trong bảng; môi trường/dependency tương thích cần smoke riêng.
```

G2 bổ sung script adapter/smoke có thể chạy lại và output thực tế. Trạng thái hiện tại của cả ba: **chưa tích hợp trong MedShield**. Source đã được nghiên cứu không đồng nghĩa engine đã chạy. Không có score mới để hiển thị trên dashboard tại G0.
