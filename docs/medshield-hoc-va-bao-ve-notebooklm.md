# MedShield — Tài liệu học dự án và chuẩn bị bảo vệ

- **Người thực hiện đề tài:** Nguyễn Tiến Đạt · Samsung Innovation Campus · AI-NIC4
- **Đề tài số 2:** Nhận diện và che thông tin định danh trong văn bản y tế
- **Mốc code dùng để giải thích:** `e06c04b`, nhánh `feat/medshield-demo` của `TdatVn-fpt/MedShield`
- **Mục đích:** Tài liệu tự chứa để đọc, ôn tập và đưa vào NotebookLM. Các đường dẫn trong dấu backtick là vị trí tra cứu trong repo.

## 1. Giới thiệu dự án trong 30 giây

MedShield xử lý một ghi chú y tế tại một thời điểm. Người dùng dán văn bản, tải TXT UTF-8 hoặc chọn PDF có lớp chữ. Hệ thống đề xuất những đoạn chứa tên, ngày sinh, số điện thoại, mã định danh hoặc địa chỉ. Người dùng rà soát, thêm đoạn còn sót, sửa nhãn hoặc bỏ đoạn bị che nhầm. Sau khi xác nhận, web tải TXT hoặc JSON chứa bản đã che. Phương pháp học máy là CRF cho tên và địa chỉ. Một bộ quy tắc có ngữ cảnh xử lý các mẫu như số điện thoại, mã và ngày sinh. Chất lượng được đo trên tập ghi chú giả lập đã khóa.

**Điểm cần nhớ khi bảo vệ:** Dự án có mô hình chạy thật và luồng web đã kiểm thử. Độ chính xác trên tập test và việc phần mềm vận hành đúng là hai kết quả khác nhau. Tập test tiếng Việt cho thấy mục tiêu F1 85% trên đủ năm nhãn vẫn chưa đạt, nên bước rà soát thủ công là một phần thiết yếu của demo.

## 2. Tôi đã làm gì trong dự án?

Dự án làm cá nhân, có Codex và Claude hỗ trợ triển khai trong các phiên làm việc. Các vai trò PM, BA, Research/ML, Dev, QA và DevOps là cách phân chia đầu việc cho agent. Khi bảo vệ, nên dùng cách nói **“trong dự án của em, em triển khai với sự hỗ trợ của Codex và Claude”**, rồi tự giải thích quyết định và chỉ ra file, kết quả. Hồ sơ hiện ghi **0 mẫu do chủ dự án trực tiếp rà soát**. Các ghi chú được agent tạo hoặc gán nhãn và có lượt kiểm chéo được ghi trong manifest và biên bản.

| Mảng công việc | Kết quả đã làm được | Tôi cần giải thích được |
|---|---|---|
| Phân tích yêu cầu | Chốt năm nhãn, luồng rà soát, quy ước vị trí, hợp đồng API và các gate | Định danh nào cần che, vì sao ngày tái khám khác ngày sinh |
| Phần mềm | Tích hợp React, Vite, FastAPI. Chạy luồng nhập → phân tích → sửa → xuất qua API thật | Lần theo nút **Phân tích** tới code backend và ngược lại |
| Quy tắc | Viết các mẫu nhận diện có ngữ cảnh, giải quyết vùng giao nhau | Regex khớp theo gì, khi nào một chuỗi số bị che nhầm |
| Học máy | Tạo dữ liệu giả lập, tách tập theo họ mẫu, huấn luyện và nạp CRF, chạy `ner` và `hybrid` trên CPU | BIO là gì, CRF học gì, cách token trở lại vị trí trong văn bản |
| Đánh giá | Chạy ba chế độ tiếng Việt trên tập test khóa và đối chứng ba công cụ tiếng Anh | Tính TP/FP/FN, lý do có hai bài đo khác nhau, điểm mạnh và lỗi thật |
| Nhập PDF | Đọc lớp chữ tại trình duyệt bằng PDF.js, chọn trang, kiểm lỗi và giữ luồng TXT | Tại sao phân tích chữ PDF khác việc xóa thông tin trên chính PDF |
| Kiểm thử và chia sẻ | Có test backend, Chromium, bản demo giả lập, biên bản nghiệm thu và nhánh trên GitHub | Đưa ra bằng chứng đã chạy và nói rõ những phần còn mở |

**Đóng góp kỹ thuật của dự án** nằm ở hợp đồng năm nhãn, dữ liệu và bài đo do dự án thiết kế, các quy tắc, huấn luyện CRF với đặc trưng của dự án, cách gộp kết quả, xử lý Unicode, luồng rà soát và bộ kiểm thử. React, FastAPI, PDF.js, CRFsuite, Presidio, Philter UCSF và GEMINI pyDeid là thư viện hoặc công cụ có sẵn. Nguồn và giấy phép nằm trong `THIRD_PARTY.md`.

## 3. Nhìn cây thư mục và biết mở đâu trước

```text
MedShield/
├── apps/
│   ├── api/                 Backend FastAPI
│   │   ├── controllers.py   Các endpoint HTTP
│   │   ├── schemas.py       Kiểu dữ liệu và kiểm tra đầu vào
│   │   ├── services/        Chọn cách nhận diện và thay đoạn đã duyệt
│   │   └── adapters/        Kết nối quy tắc và CRF
│   └── web/                 Frontend React, TypeScript và Vite
│       ├── src/             Màn hình, trạng thái, gọi API và đọc PDF
│       └── e2e/             Test Playwright và PDF giả lập cho test
├── ml/                      Huấn luyện, suy luận, tính điểm và đối chứng
│   └── upstream/            Worker và cấu hình đối chứng tiếng Anh
├── data/                    Dữ liệu giả lập đầu vào, nhãn vàng và manifest
├── artifacts/               Trọng số và kết quả đánh giá do chương trình tạo
├── tests/                   Test Python
├── scripts/                 Lệnh lặp lại công việc và tạo mẫu demo
├── docs/                    Hướng dẫn, kiến trúc, báo cáo và bằng chứng
├── specs/                   Đặc tả, kế hoạch và task theo Spec Kit
├── .specify/                Constitution, template và script Spec Kit
└── .agents/                 Hướng dẫn thao tác cho agent phát triển
```

| Tôi muốn tìm… | Mở file hoặc thư mục nào? |
|---|---|
| Trang chính và các nút | `apps/web/src/App.tsx` |
| Ô nhập, tô màu, thêm vùng thủ công | `apps/web/src/SourcePanel.tsx`, `DetectionList.tsx`, `PreviewPanel.tsx` |
| Lệnh web gọi backend | `apps/web/src/useReview.ts`, `apps/web/src/api.ts` |
| Quy trình nhập PDF | `PdfImportControls.tsx`, `usePdfImport.ts`, `pdfDocument.ts`, `pdfPolicy.ts` trong `apps/web/src/` |
| Cách server chạy và trả lỗi | `apps/api/main.py`, `apps/api/controllers.py`, `apps/api/schemas.py` |
| Regex và thứ tự ưu tiên | `apps/api/adapters/rules.py`, `apps/api/services/analysis.py` |
| Nạp CRF và lấy dự đoán | `apps/api/adapters/ner.py`, `ml/model.py` |
| Code huấn luyện | `ml/tokenization.py`, `ml/bio.py`, `ml/features.py`, `ml/train.py` |
| Mã đo và điểm thực tế | `ml/scoring.py`, `ml/evaluate.py`, `artifacts/evaluation.json`, `docs/experiment.md` |
| File demo để bấm thử | `docs/evidence/demo-benh-an-ngoai-tru.pdf`, bản `.txt` tương ứng, cùng `.reviewed.txt` và `.reviewed.json` |
| Quy ước và tiến độ | `AGENTS.md`, `docs/spec.md`, `docs/api-contract.md`, `docs/progress.md`, `docs/tasks.md`, `docs/reviews/` |

### Vì sao VS Code của tôi có nhiều thư mục bắt đầu bằng dấu chấm?

| Tên trong ảnh | Mục đích |
|---|---|
| `.agents/`, `.specify/` | Hai thư mục được quản lý trong Git. Chúng phục vụ việc phát triển theo đặc tả. |
| `.claude/` | Tệp làm việc cục bộ của Claude trong checkout được kiểm. Hiện chưa được theo dõi trong Git. |
| `.venv/` | Môi trường Python chính do `uv` cài để chạy API, ML và test. |
| `.venv-g2-t204/`, `.venv-g2-t204-final/` | Môi trường phụ tạo trong lúc kiểm lại cài đặt và suy luận ở G2. |
| `.venv-upstream/`, `.venv-upstream-g2/` | Môi trường phụ phục vụ cài đặt/thử công cụ đối chứng tiếng Anh. Gói của từng công cụ có thể cần phiên bản khác. |
| `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/` | Cache do công cụ kiểm kiểu, kiểm thử và lint tạo để chạy lại nhanh. |
| `.env.example` | Mẫu cấu hình để đọc và tham khảo. Lệnh khởi động hiện truyền host và port bằng tham số; `MEDSHIELD_MODEL_DIR` là tùy chọn chỉ thư mục trọng số. |
| `.python-version`, `pyproject.toml`, `uv.lock` | Phiên bản Python dùng trong dự án, khai báo dependency và bản khóa để cài lại. Frontend có `package.json` và `package-lock.json`. |
| `.gitignore`, `.gitattributes` | File thứ nhất loại cache và môi trường khỏi Git. File thứ hai chuẩn hóa cách Git xử lý tệp, gồm giữ nguyên byte PDF trên Windows. |

Phân biệt **`data/` là nguyên liệu**, **`ml/` là code xử lý**, **`artifacts/` là kết quả sinh ra**. Ví dụ `data/test.jsonl` chứa đáp án vàng, `ml/scoring.py` chấm dự đoán, còn `artifacts/evaluation.json` là kết quả dashboard dùng.

## 4. Theo dấu một lần bấm Phân tích

```text
PDF / TXT / văn bản dán
      ↓
SourcePanel → useReview → requestJson → POST /api/analyze
      ↓                                   ↓
Hiển thị đề xuất              controller → Pydantic → analysis.py
      ↑                                               ↓
Entity + preview ← chuẩn hóa vùng ← rules / CRF / hybrid
      ↓
Rà soát → POST /api/redact → preview mới → xác nhận → TXT/JSON
```

1. `SourcePanel.tsx` đưa phần chữ vào trạng thái do `useReview.ts` quản lý. Với PDF, trình duyệt trích chữ trước.
2. Khi bấm **Phân tích**, `useReview.analyze()` gửi `{text, language, mode}` qua `api.ts`. Vite proxy từ web cổng 5173 sang API cổng 8000.
3. `controllers.py` nhận request. Pydantic kiểm kiểu, nhãn, giới hạn và trường lạ trong `schemas.py`. `analysis.py` chọn đúng chế độ. Nếu mode cần CRF mà trọng số chưa nạp được, API trả `503 ENGINE_UNAVAILABLE`.
4. Kết quả có `entities`, `redacted_text` và `engine`. Web lấy entity để tô vùng, hiển thị nguồn và gọi `/api/redact` để có preview cùng metadata cho bộ vùng đang xét.
5. Đổi nhãn, thêm hoặc xóa vùng tạo danh sách mới. `/api/redact` chỉ dùng danh sách gửi lên, giữ đúng quyết định của người rà soát. Khi có preview hợp lệ và đã xác nhận, `downloadResult()` tạo tệp từ nội dung hiện hành.

| Endpoint | Ý nghĩa |
|---|---|
| `GET /health` | Kiểm API và trạng thái từng cặp ngôn ngữ/chế độ. |
| `POST /api/analyze` | Chạy engine trên nguyên văn và đề xuất vùng che. |
| `POST /api/redact` | Kiểm danh sách vùng do web gửi rồi tạo bản đã che cùng metadata. |
| `GET /api/evaluation` | Đọc artifact thực nghiệm đã có hoặc báo `unavailable`. |

**Liên hệ ASP.NET MVC:** `controllers.py` giống Controller, `schemas.py` gần ViewModel, `services/` là tầng nghiệp vụ, `adapters/` chuẩn hóa công cụ bên dưới và React là View. CRF là mô hình học máy. `Entity` là kiểu dữ liệu truyền giữa các tầng.

## 5. Các kỹ thuật cốt lõi cần tự giải thích

### 5.1 Năm nhãn và quy tắc theo ngữ cảnh

`NAME` là tên người, `DOB` là ngày/năm sinh, `PHONE` là số điện thoại, `ID` là mã định danh thuộc phạm vi gán nhãn, `ADDR` là địa chỉ. Gán đúng **giá trị**. Ví dụ `Ngày sinh: 20/02/1985` chỉ che `20/02/1985`. `Hẹn tái khám: 18/12` giữ nguyên. Xem `docs/annotation-guide.md` để phân biệt ID người bệnh với mã bệnh ICD và địa chỉ cá nhân với địa danh trong nội dung chuyên môn.

`rules.py` dùng biểu thức chính quy và từ dẫn. Regex phù hợp với chuỗi có dạng tương đối rõ như ngày hoặc mã. Khi ngữ cảnh thay đổi, quy tắc có thể nhận dư tiền tố hoặc nhận nhầm một dãy số có hình dáng giống điện thoại. `rules` cũng có ứng viên NAME và ADDR. Đây là đường cơ sở để so sánh.

### 5.2 NER, BIO và CRF khác nhau thế nào?

- **NER** là bài toán tìm thực thể và gán loại cho đoạn văn bản.
- **BIO** là cách biểu diễn đoạn bằng nhãn trên từng token. `B-NAME` là token đầu một tên, `I-NAME` là token tiếp theo của cùng tên và `O` là bên ngoài thực thể. `ADDR` có cặp tương ứng.
- **CRF tuyến tính** là mô hình học có giám sát cho chuỗi nhãn. Nó dùng đặc trưng của token và điểm chuyển giữa các nhãn liền kề để chọn một chuỗi nhãn cho cả câu. CRF của MedShield học từ các đoạn `NAME` và `ADDR` đã gán nhãn. Dự đoán chạy trên CPU.

Ví dụ học BIO với `Họ và tên: Hạ Minh.`. Minh họa các token quan trọng: `Họ / O`, `và / O`, `tên / O`, `: / O`, `Hạ / B-NAME`, `Minh / I-NAME`, `. / O`. Sau dự đoán, lấy biên từ đầu `Hạ` tới cuối `Minh` để thu lại một đoạn `NAME`.

**Đường huấn luyện và suy luận:** `tokenization.py` tạo token giữ vị trí → `bio.py` chuyển vùng vàng sang nhãn token → `features.py` tạo đặc trưng → `train.py` huấn luyện và chọn cấu hình trên validation → lưu `model.crfsuite` với `metadata.json` → `CrfModel.predict()` suy luận → adapter trả entity đúng format API. Đặc trưng gồm chữ thường, tiền tố/hậu tố, viết hoa, chữ số, token lân cận tối đa ba vị trí mỗi phía và dấu xuống dòng. Chuẩn hóa NFC dùng trong đặc trưng; vị trí vẫn tính trên nguyên văn. Cấu hình được chọn là `lbfgs`, `c1=0.05`, `c2=0.1`, tối đa 100 vòng, có trong metadata. Revision SHA-256 cho biết byte trọng số nào đã chạy.

### 5.3 Hybrid gộp hai nguồn như thế nào?

`hybrid` chạy CRF và rules trên **cùng văn bản gốc**. Các đề xuất giao nhau được ưu tiên theo thứ tự: `DOB/PHONE/ID` từ rules → `NAME/ADDR` từ CRF → `NAME/ADDR` từ rules. Trong cùng mức ưu tiên, ưu tiên điểm cao hơn rồi đoạn dài hơn. Đầu ra được sắp theo vị trí và vẫn giữ `source`. `ner` và `hybrid` hiện chỉ khả dụng cho `vi`. `rules` có cấu hình `vi` và `en`. Presidio, Philter và pyDeid nằm ở đường đối chứng Anh ngữ riêng.

### 5.4 Span, Unicode và cách thay token

`start` tính từ 0 và có tính ký tự đầu. `end` chỉ vị trí ngay sau ký tự cuối. Ví dụ với `🙂 Mai An`, `Mai An` ở `[2,8)` theo **Unicode code point**. Emoji này dùng hai đơn vị UTF-16 trong JavaScript, nên vị trí theo UTF-16 là `[3,9)`. Dùng nhầm hệ đếm có thể che lệch. `unicode.ts` chuyển vùng DOM selection sang code point và ngăn cắt giữa một cặp surrogate. Dấu tổ hợp có thể hiện như một chữ nhưng gồm nhiều code point, vì vậy vị trí luôn tính trên chính chuỗi đưa vào API.

`redaction.py` sắp vùng theo vị trí, từ chối vùng ngoài biên, rỗng, trùng hoặc chồng nhau. Sau đó ghép đoạn còn nguyên và ký hiệu từ trái sang phải để vị trí gốc luôn có nghĩa. Khóa token là **(nhãn, đúng chuỗi gốc)**. Nếu cả hai lần `Mai An` đều được đánh dấu `NAME`, chúng cùng là `[NAME_1]`. `mai an` là chuỗi khác. Sang tài liệu mới, bộ đếm bắt đầu lại.

### 5.5 Bất đồng bộ, quyền riêng tư và giới hạn

- **Chặn kết quả cũ:** `useReview.ts` kiểm revision của tác vụ. Nếu người dùng đổi văn bản hoặc vùng che khi request đang chạy, response cũ không được áp dụng. `usePdfImport.ts` dùng phiên nhập và `AbortController` để hủy worker khi cần và bỏ qua PDF đọc xong muộn.
- **Che tại chỗ rồi xuất:** API và trình duyệt giữ nội dung làm việc trong bộ nhớ. JSON tải về chỉ có `redacted_text` và `metadata`. Metadata chứa đếm vùng theo nhãn và đơn vị vị trí, không chứa bản đồ thay tên. Các ca kiểm tra dùng hồ sơ giả lập.
- **Giới hạn kỹ thuật:** PDF tối đa 10 MiB, mỗi lượt tối đa 10 trang và phần chữ tối đa 50.000 code point. API cũng giới hạn tối đa 2.000 vùng che. PDF hỏng, khóa mật khẩu hoặc trang thiếu lớp chữ có thông báo tương ứng. Hệ thống chưa làm OCR hay xóa chữ trên chính tài liệu PDF gốc. Dùng bản đã rà soát khi xuất. Không suy ra hồ sơ đã ẩn danh hoàn toàn vì mẫu có thể còn sót định danh hoặc chứa thông tin ngoài năm nhãn.

### 5.6 PDF.js làm gì trong trình duyệt?

Nút nhập mở file cục bộ. `pdfDocument.ts` dùng PDF.js trong worker được Vite đóng gói, nạp khi cần, đọc chữ các trang chọn và gom đoạn theo hàng/vị trí ngang để đưa vào ô nhập. Tệp PDF gốc không được gửi lên API; request phân tích gửi phần chữ sau khi người dùng bấm **Phân tích**. Nhập PDF là một nguồn văn bản mới cho cùng pipeline AI. Với bảng nhiều cột, phải kiểm lại thứ tự trường. PDF mẫu hai trang học theo bố cục mẫu ngoại trú `15/BV-01`, có chữ chọn được và nhãn **DỮ LIỆU GIẢ LẬP**.

## 6. Học cách đọc số liệu của chính MedShield

### Dữ liệu và chia tập

| Tập | Ghi chú | Họ mẫu | Vùng vàng | Dùng để làm gì |
|---|---:|---:|---:|---|
| Tiếng Việt train | 60 | 10 | 108 | Học trọng số CRF |
| Tiếng Việt validation | 20 | 4 | 45 | Chọn cấu hình |
| Tiếng Việt test | 20 | 6 | 33 | Đo ba chế độ đã chốt |
| Tiếng Anh đối chứng | 16 | 16 | 32 | So ba công cụ tiếng Anh theo vùng che |

Một mẫu là **một ghi chú**, có thể có nhiều vùng hoặc không có vùng nào. Tập tiếng Việt tổng cộng **100 ghi chú**, gồm 60/20/20. Chia theo **họ mẫu** trước khi sinh các biến thể để văn phong và cấu trúc gần như giống hệt nhau không rơi vào cả train và test. Seed sinh train/validation là `20261121`. Test tiếng Việt do QA soạn và BA đối chiếu. Việc chấm diễn ra trước các sửa tay trên web.

### Công thức và ví dụ tính

- **TP:** dự đoán khớp đúng. **FP:** một dự đoán không khớp. **FN:** một vùng vàng bị thiếu một dự đoán khớp.
- **Precision** = `TP / (TP + FP)`. Trong các vùng máy đề xuất, bao nhiêu vùng đúng?
- **Recall** = `TP / (TP + FN)`. Trong các vùng cần phát hiện, máy tìm đúng bao nhiêu vùng?
- **F1** = `2 × TP / (2 × TP + FP + FN)`. Micro-F1 cộng TP/FP/FN trước rồi tính, vì vậy khác trung bình F1 của từng nhãn. **Support** là số vùng vàng, hoặc số vị trí vàng nếu chấm theo ký tự.
- Ví dụ vàng `[2,8,NAME]`, máy đưa `[2,7,NAME]`. Đo exact span + label ghi **1 FP và 1 FN** vì lệch biên. Đổi nhãn sai cũng cho kết quả tương tự.
- Ví dụ số thật của hybrid: `TP=13`, `FP=4`, `FN=20`. Precision = `13/17 = 76,47%`, recall = `13/33 = 39,39%`, F1 = `26/(26+4+20) = 52,00%`.

### Tiếng Việt · exact span + label trên 20 ghi chú test

| Cấu hình | TP | FP | FN | Precision | Recall | Micro-F1 | Ghi chú còn ít nhất một FN |
|---|---:|---:|---:|---:|---:|---:|---:|
| Rules | 1 | 8 | 32 | 11,11% | 3,03% | 4,76% | 15/20 |
| NER | 12 | 0 | 21 | 100,00% | 36,36% | 53,33% | 12/20 |
| Hybrid | 13 | 4 | 20 | 76,47% | 39,39% | 52,00% | 11/20 |

| Nhãn | Support | F1 Rules | F1 NER | F1 Hybrid |
|---|---:|---:|---:|---:|
| NAME | 17 | 0,00% | 69,23% | 69,23% |
| DOB | 4 | 0,00% | 0,00% | 0,00% |
| PHONE | 4 | 0,00% | 0,00% | 0,00% |
| ID | 5 | 33,33% | 0,00% | 33,33% |
| ADDR | 3 | 0,00% | 100,00% | 100,00% |

NER đạt precision 100% trong lần đo này vì 12 dự đoán đều khớp, nhưng còn 21 FN. Hybrid bổ sung một ID đúng và bốn PHONE sai so với NER. Nó tăng recall và giảm từ 12 xuống 11 ghi chú có FN, còn micro-F1 giảm. ADDR đạt 100% chỉ có **3 vùng vàng**. DOB và PHONE nhận F1 bằng 0 trên test đã khóa. Không dùng ca demo dễ hơn để suy ra chất lượng toàn bộ. Ví dụ lỗi thực nằm ở `docs/experiment.md`: rules che thừa tiền tố địa chỉ, nhận số lưu kho thành điện thoại, còn NER/hybrid có thể bỏ sót tên viết thường.

### Tiếng Anh · vùng che trên 16 ghi chú

Các công cụ nhận cùng nguyên văn một cách độc lập. Phép chấm đo các vị trí Unicode **ngoài khoảng trắng** thuộc hợp vùng che, gồm **399 vị trí vàng** từ 32 vùng. Bảng dưới không dùng đơn vị thực thể của bảng tiếng Việt.

| Công cụ | TP | FP | FN | Micro-F1 vùng che | Ghi chú còn FN |
|---|---:|---:|---:|---:|---:|
| Presidio | 267 | 237 | 132 | 59,14% | 9/16 |
| Philter UCSF | 341 | 132 | 58 | 78,21% | 12/16 |
| GEMINI pyDeid | 195 | 100 | 204 | 56,20% | 11/16 |

Presidio chạy Analyzer với mô hình spaCy tiếng Anh. Philter cho vùng che theo mask, sau đó adapter căn lại vị trí. GEMINI pyDeid chạy bộ quy tắc với `named_entity_recognition=False`. Philter có điểm vùng che cao nhất trong lần chạy này và vẫn bỏ sót ít nhất một vị trí ở 12/16 ghi chú. Khi nói số liệu, nêu **ngôn ngữ, tập mẫu và đơn vị chấm** cùng điểm.

## 7. Cách chạy, kiểm thử và tự học bằng thao tác thật

Mở hai PowerShell trong checkout MedShield. Nếu repo ở `D:\Workspace\MedShield`, dùng các lệnh sau.

**Cửa sổ API**

```powershell
Set-Location D:\Workspace\MedShield
uv sync --locked --python 3.11.7
uv run --locked uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

**Cửa sổ web**

```powershell
Set-Location D:\Workspace\MedShield\apps\web
npm ci
npm run dev
```

Mở `http://127.0.0.1:5173/`. Kiểm tra `http://127.0.0.1:8000/health` nếu web báo API chưa chạy. Lỗi cổng đã được sử dụng có thể do dịch vụ đang mở ở terminal khác. Lỗi npm `ENOENT` thường xảy ra khi chạy npm trong `apps/` thay vì `apps/web/`.

**Tập demo ba phút:** chọn **Nhập PDF** → `docs/evidence/demo-benh-an-ngoai-tru.pdf` → trang **1–2** → **Trích văn bản** → chọn **Tiếng Việt / Kết hợp · hybrid** → **Phân tích**. So chữ với PDF gốc. Trong lần kiểm, năm vùng thuộc năm nhãn được đề xuất và `tạ hư cấu` còn nguyên. Bôi đen tên đó, chọn `NAME`, bấm **Thêm vùng che**. Xác nhận rồi tải TXT. Chỉ ra `[NAME_2]`, tổng 6 vùng đã che và ngày tái khám `18/12` còn nguyên. Lần kiểm độc lập ở 390px và 1440px tải TXT 623 byte và JSON 873 byte khớp bản bàn giao.

**Kiểm từ gốc repo:**

```powershell
uv run --locked pytest -q
uv run --locked python scripts/check_source.py
uv run --locked python -m ml.evaluate --output-dir artifacts/local/hoc-g3
```

Lệnh cuối chạy lại bài đo Việt, ghi file vào thư mục riêng để so với artifact công bố. Nếu muốn đánh giá lại tiếng Anh, cài môi trường bằng `scripts/setup-upstream.ps1` rồi dùng `scripts/evaluate-upstream.ps1` theo `docs/upstream.md`.

**Kiểm từ `apps/web/`:**

```powershell
npx playwright install chromium
npm run test:e2e -- pdf-import.spec.ts
npm run typecheck
npm run build
```

Biên bản PDF ghi lần kiểm lại Windows có **55/55 test backend và 22/22 test Chromium qua**, trong đó 9 test PDF. Test API kiểm hợp đồng, vị trí và dữ liệu lỗi. Test browser kiểm nhập thật, request thật, thao tác sửa, xác nhận, bytes tải xuống, hai kích thước và đường lỗi. Kiểm riêng `.gitattributes` vì Git có thể đổi LF thành CRLF làm sai vị trí byte nội bộ của PDF.

## 8. Phần đã nghiệm thu và phần còn mở

| Chặng | Kết luận ở mốc code trong tài liệu |
|---|---|
| G0 | PASS cho repo, môi trường, đặc tả và kế hoạch. |
| G1 | PASS cho nhập TXT/dán văn bản, phân tích, rà soát và xuất thật. |
| G2 | PASS cho rules/NER/hybrid và các smoke upstream. |
| G3 | PASS cho quy trình tái tạo và kiểm chứng kết quả. Mục tiêu F1 85% trên đủ năm nhãn tiếng Việt chưa đạt. |
| G4 | PDF-01–PDF-04 PASS. G4 tổng thể còn hạng mục Three.js và nghiệm thu theo phạm vi G4. |
| G5 | Bàn giao toàn dự án như CI, ZIP và nghiệm thu checkout sạch theo G5 còn mở. Code và README đã được đẩy lên nhánh `feat/medshield-demo`. |

## 9. Luyện bảo vệ và luyện với NotebookLM

| Câu hỏi dễ gặp | Ý trả lời bằng lời của mình |
|---|---|
| AI nằm ở đâu? | Ở CRF trong `ml/` và đường gọi qua adapter NER. Mô hình học nhãn BIO cho tên và địa chỉ. Regex xử lý các mẫu có quy tắc. |
| Dùng bao nhiêu mẫu? | 100 ghi chú Việt chia 60/20/20. Test có 20 ghi chú và 33 vùng vàng. Bài đối chứng tiếng Anh tách riêng, có 16 ghi chú. |
| F1 tốt nhất là bao nhiêu? | Micro-F1 Việt cao nhất là 53,33% ở NER. Hybrid 52%, nhưng phát hiện thêm một vùng đúng và giảm một ghi chú có FN. Mục tiêu 85% chưa đạt trên đủ năm nhãn. |
| Vì sao dùng ba công cụ Anh ngữ? | Để có bài đối chứng độc lập trên cùng corpus. Ba công cụ được so theo code point vùng che vì đầu ra nhãn không đồng nhất. |
| Vì sao không gửi nguyên PDF đến API? | Trình duyệt trích chữ và cho người dùng đối chiếu trước. API phân tích đúng chuỗi đang hiển thị và dùng lại pipeline TXT. |
| Có thể chia sẻ ngay sau khi bấm Phân tích không? | Cần rà soát vì có FN, FP và dữ liệu ngoài phạm vi năm nhãn. Chỉ nút xuất sau xác nhận mới tạo tệp cho phiên hiện hành. |
| Phần nào là đóng góp của đề tài? | Chỉ rõ dữ liệu giả lập, pipeline CRF, quy tắc/hybrid, hợp đồng vị trí, luồng rà soát và bộ đánh giá. Nêu thư viện dùng lại và sự hỗ trợ của Codex/Claude. |

**Bài tập tự làm:**

1. Mở `App.tsx`, tìm nút **Phân tích**, theo đến `useReview.ts`, rồi tìm handler trong `controllers.py`. Tự vẽ lại đường đi bằng 5 ô.
2. Viết ra các token cho `Họ và tên: Hạ Minh.`, gán BIO, rồi tìm `start/end` theo code point. Thêm emoji đứng đầu và giải thích vì sao index JavaScript thay đổi.
3. Tự tính precision, recall, F1 từ `13/4/20`. Giải thích vì sao chỉ số 100% precision của NER không có nghĩa là tìm hết định danh.
4. Demo PDF, thêm tên bị sót, mở TXT. Sau đó sửa văn bản gốc và kiểm xem bản che cũ còn được tải hay không.

**Prompt để dán vào NotebookLM:**

> Dựa trên tài liệu MedShield này, dạy tôi từ luồng web đến CRF và cách đo F1. Mỗi lần giải thích hãy dẫn đường dẫn file, cho một ví dụ, rồi hỏi tôi một câu để tự trả lời. Phân biệt phần đã nghiệm thu, kết quả đo, thư viện tái sử dụng và phần còn mở. Giữ đúng số mẫu, đơn vị chấm và nhãn mà CRF hỗ trợ.

> Đóng vai giảng viên và hỏi tôi 10 câu từ cơ bản đến khó. Bắt đầu với cách bấm nút Phân tích, sau đó hỏi BIO, Unicode, train/validation/test, precision/recall/F1, giới hạn PDF và vai trò của người rà soát. Hãy đợi tôi trả lời từng câu mới sửa và hỏi tiếp.

### Nguồn kiểm lại trong repo

- `README.md`, `docs/architecture.md`, `docs/spec.md`, `docs/api-contract.md`, `docs/annotation-guide.md`.
- `docs/engines.md`, `docs/experiment.md`, `docs/upstream.md`, `artifacts/evaluation.json`, `artifacts/model/metadata.json`, `data/test-manifest.json`, `data/train-validation-manifest.json`.
- `docs/contributions.md`, `THIRD_PARTY.md`, `docs/progress.md`, `docs/reviews/G1.md`, `docs/reviews/G2.md`, `docs/reviews/G3.md`, `docs/reviews/G4-pdf.md`, `docs/huong-dan-nhap-pdf.md`.
