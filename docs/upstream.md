# Đối chứng upstream trên Windows

T203 · DevOps · READY_FOR_REVIEW. Research/QA kiểm tra độc lập.

## Cài và chạy

Từ gốc checkout MedShield trên Windows x64, dùng PowerShell, Git và uv. Các lệnh dưới đây đã được thử với Windows PowerShell 5.1 và uv 0.11.21. Lần cài đầu cần truy cập nguồn package, Python và tài nguyên trên GitHub.

```powershell
powershell.exe -NoProfile -File .\scripts\setup-upstream.ps1
powershell.exe -NoProfile -File .\scripts\setup-upstream.ps1 -SmokeOnly
```

Lệnh đầu tạo ba venv trong `.venv-upstream-g2/`, đồng bộ và kiểm tra dependency từ các lock theo engine trong `ml/upstream/`, sau đó chạy cả ba smoke. uv chọn hoặc tải đúng phiên bản CPython. Có thể chạy lại lệnh đầu để đồng bộ môi trường. `-SmokeOnly` dùng các venv và tài nguyên đã cài.

Script chuẩn bị checkout `philter` dưới thư mục sibling `MedShield-upstream` khi cần. Với checkout có sẵn, script kiểm tra origin, SHA và thay đổi trên file tracked. Dùng `-UpstreamRoot` để chỉ định thư mục khác. Tài nguyên POS tagger nằm trong `.venv-upstream-g2/philter/nltk_data/`. Script tải [archive NLTK chính thức](https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/taggers/averaged_perceptron_tagger_eng.zip) và kiểm SHA-256 của archive và ba file JSON.

Chạy lại riêng từng engine sau khi cài

```powershell
powershell.exe -NoProfile -File .\scripts\setup-upstream.ps1 -SmokeOnly -Engine presidio
powershell.exe -NoProfile -File .\scripts\setup-upstream.ps1 -SmokeOnly -Engine philter
powershell.exe -NoProfile -File .\scripts\setup-upstream.ps1 -SmokeOnly -Engine pydeid
```

Với `-SmokeOnly`, stdout có một mảng JSON cho mỗi engine chạy thành công, theo thứ tự Presidio, Philter, GEMINI pyDeid khi chạy cả ba. Mỗi phần tử có đúng hai trường nguyên `start` và `end`, dùng Unicode code point `[start,end)`. Nếu một engine lỗi, script ghi tên engine và lý do vào stderr, tiếp tục các engine còn lại và trả exit 1.

## Nguồn và phạm vi thực thi

| Engine | Môi trường và lời gọi |
| --- | --- |
| Presidio Analyzer | CPython 3.11.7, gói `presidio-analyzer==2.2.366`, [source tham chiếu MIT](https://github.com/data-privacy-stack/presidio/tree/9fc7774ed74faa0afd5ffb36da63e77b9a2f8c30). Gọi `AnalyzerEngine.analyze` với cấu hình tiếng Anh, recognizer mặc định cho `en`, spaCy 3.7.5 và [model `en_core_web_sm==3.7.1` (MIT)](https://github.com/explosion/spacy-models/releases/tag/en_core_web_sm-3.7.1). Cấu hình tường minh giúp dùng đúng model đã pin thay cho `en_core_web_lg` mặc định. |
| Philter UCSF | CPython 3.10.20, [source BSD-3-Clause tại SHA đã pin](https://github.com/BCHSI/philter-ucsf/tree/4da3cf31c9bfbfd66c66b141c45ba7a47628dd0a). Gọi `main.py -f configs/philter_delta.json --prod=True --outputformat asterisk` từ checkout, với input/output tạm riêng và POS cache trong bộ nhớ. Khi thử trên Python 3.11, Philter thất bại vì regex có cờ toàn cục giữa biểu thức. Python 3.10 chạy được source giữ nguyên. Lock Windows thay các pin cũ của upstream bằng NLTK 3.9.2, chardet 5.2.0, NumPy 1.26.4, pandas 2.2.3 và xmltodict 0.14.2. |
| GEMINI pyDeid | CPython 3.11.7, `pyDeid==1.0.1` từ [git URL và SHA GEMINI, MIT](https://github.com/GEMINI-Medicine/pyDeid/tree/f93d2ddb1fd857236b2d3b4b761af2b8028c7281). Gọi `deid_string(..., named_entity_recognition=False)` và đọc `phi_start/phi_end` trên chuỗi gốc. NumPy 1.26.4 tương thích ABI spaCy 3.7.5, Click 8.5.1 đáp ứng import của spaCy, setuptools 80.9.0 cung cấp `pkg_resources` cho wordlist. |

## Fixture và kết quả thực tế

`ml/upstream/smoke.py` chứa một ghi chú tiếng Anh ASCII dài 85 code point, do DevOps tạo riêng cho smoke. Số điện thoại dùng dải hư cấu 555-01xx. SHA-256 của UTF-8 fixture là `e789cec5cb91c8f1ee67b6fb9c62c3f467fbd68674c436a4d739d3a402615c94`. Mỗi engine nhận cùng chuỗi gốc. CLI chỉ nhận tên engine và đường dẫn tài nguyên. Philter dùng file tạm trong thời gian chạy; worker loại bỏ stdout/stderr upstream và chỉ in các vị trí. Bản che và bảng surrogate không xuất hiện trong kết quả.

Đơn vị đối chứng là vùng che theo code point ngoài whitespace. Presidio và pyDeid chuyển các span gốc thành hợp vùng. Philter đối chiếu mask dấu sao với ghi chú gốc và yêu cầu vị trí căn đúng. Hai dấu gạch trong số điện thoại được Philter giữ nguyên, nên vùng số điện thoại tách thành ba khoảng. Smoke yêu cầu mọi chữ số trong số điện thoại giả lập được che. Kết quả là bằng chứng suy luận G2, chưa dùng để tính điểm chất lượng G3.

Lệnh đã chạy từ ba venv mới và checkout Philter mới tại đường dẫn có khoảng trắng. uv dùng cache sẵn có. Cả ba dependency check đều thành công và script kết thúc exit 0.

```powershell
powershell.exe -NoProfile -File .\scripts\setup-upstream.ps1 -UpstreamRoot 'artifacts/local/upstream setup check'
```

Kiểm tra đường lỗi với `-SmokeOnly` và thư mục Philter thiếu cho exit 1. stderr có chẩn đoán Philter, stdout vẫn có kết quả thực của Presidio và pyDeid.

Các vị trí quan sát được trong lần chạy thành công

| Engine | Khoảng `[start,end)` quan sát được |
| --- | --- |
| Presidio | `[9,14) [15,22) [24,27) [29,39) [48,60) [75,78) [79,84)` |
| Philter | `[9,14) [15,22) [29,31) [32,34) [35,39) [48,51) [52,55) [56,60)` |
| GEMINI pyDeid | `[29,39) [48,60)` |

## Thử Philter trên hai ghi chú tiếng Anh có Unicode hoặc CRLF

Đã lấy trường `text` theo `note_id` trong `data/english.jsonl`, ghi đúng byte UTF-8 vào thư mục tạm, chạy CLI Philter với cấu hình như trên rồi đọc byte đầu ra để so sánh với nguyên văn. Không tính điểm hay sửa corpus.

| Ghi chú | Kết quả trên Windows |
| --- | --- |
| `en-003` | CLI exit 0, giữ 144 code point và cả 4 cặp CRLF trong file đầu ra. Các khác biệt đều là dấu sao sau khi so sánh với văn bản gốc. Philter đọc bằng chế độ newline mặc định của Python, vì vậy kết quả này chỉ xác nhận căn vị trí trên ca CRLF đã thử. |
| `en-005` | CLI exit 0 nhưng chardet chọn Windows-1254 cho UTF-8. Đầu ra thành 151 code point thay vì 147, nên không thể dùng vị trí từ mask này. Thử lại với cùng byte đầu vào và chỉ buộc bộ đọc Philter dùng UTF-8 trong tiến trình thử nghiệm. Đầu ra khi đó có 147 code point và căn đúng. Philter giữ nguyên emoji tại vị trí 0 và dấu tổ hợp tại vị trí 25 dù dấu này nằm trong span vàng. Hàm tạo mask dấu sao của upstream chỉ thay ký tự chữ/số ASCII. |

Giới hạn ASCII/LF vẫn áp dụng cho fixture smoke G2. Với corpus G3 hiện tại, CLI mặc định không cho vị trí hợp lệ trên `en-005`. Chỉ định UTF-8 xử lý lệch vị trí ở ca này, còn dấu tổ hợp vẫn nằm ngoài khả năng che của mask upstream. Research và BA có thể dùng kết quả này khi quyết định revision corpus tiếng Anh trước lần chấm đầu tiên.
