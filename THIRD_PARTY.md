# Nguồn, phiên bản và giấy phép

Research/ML lập bản sơ bộ 18/11/2026 (Asia/Saigon), READY_FOR_REVIEW. Bảng phân biệt mã đã dùng với nguồn chỉ điều tra. Phiên bản cài thực tế cuối cùng lấy từ `uv.lock`, `apps/web/package-lock.json` và smoke artifacts; không suy ra đã chạy từ bảng này.

Cả ba adapter đã chạy trên cùng ghi chú tiếng Anh giả lập ở G2. Lệnh cài, nguồn tài nguyên, phiên bản và vị trí quan sát được nằm trong [bằng chứng upstream](docs/upstream.md). Model spaCy `en_core_web_sm` 3.7.1 có giấy phép MIT và wheel khoảng 12,2 MiB.

| Thành phần | Nguồn/revision kiểm tra | Giấy phép | Phạm vi/trạng thái hiện tại |
|---|---|---|---|
| Presidio Analyzer | [data-privacy-stack/presidio](https://github.com/data-privacy-stack/presidio/tree/9fc7774ed74faa0afd5ffb36da63e77b9a2f8c30), gói 2.2.366 | [MIT](https://github.com/data-privacy-stack/presidio/blob/9fc7774ed74faa0afd5ffb36da63e77b9a2f8c30/LICENSE) | Đã chạy smoke đối chứng tiếng Anh với spaCy 3.7.5 và `en_core_web_sm` 3.7.1. |
| Philter UCSF | [BCHSI/philter-ucsf](https://github.com/BCHSI/philter-ucsf/tree/4da3cf31c9bfbfd66c66b141c45ba7a47628dd0a) | [BSD-3-Clause](https://github.com/BCHSI/philter-ucsf/blob/4da3cf31c9bfbfd66c66b141c45ba7a47628dd0a/LICENSE) | Đã chạy smoke đối chứng tiếng Anh trên CPython 3.10.20 với cấu hình `philter_delta`. |
| GEMINI pyDeid | [GEMINI-Medicine/pyDeid](https://github.com/GEMINI-Medicine/pyDeid/tree/f93d2ddb1fd857236b2d3b4b761af2b8028c7281), gói 1.0.1 | [MIT](https://github.com/GEMINI-Medicine/pyDeid/blob/f93d2ddb1fd857236b2d3b4b761af2b8028c7281/LICENSE.md) | Đã chạy smoke đối chứng tiếng Anh bằng `deid_string` ở chế độ quy tắc. Git URL, SHA và phiên bản được xác minh khi chạy. |
| sklearn-crfsuite / python-crfsuite | [sklearn-crfsuite 0.5.0](https://pypi.org/project/sklearn-crfsuite/0.5.0/) và [python-crfsuite 0.9.12](https://pypi.org/project/python-crfsuite/0.9.12/) | MIT, theo metadata cài đặt | `uv.lock` khóa cả hai gói. `python-crfsuite` hỗ trợ huấn luyện và suy luận với trọng số định dạng CRFsuite. |
| phonenumbers | [phonenumbers 9.0.40](https://pypi.org/project/phonenumbers/9.0.40/), bản Python của Google libphonenumber | Apache-2.0 | Kiểm cấu trúc số vùng VN cục bộ. Gói và hash phát hành khóa trong `uv.lock`. |
| GitHub Spec Kit | [github/spec-kit](https://github.com/github/spec-kit/tree/59d61c59630c3bd5a294f4c23e43a60d8ab98d02), CLI 1.4.3.dev0 | MIT | Tech Lead đã scaffold integration Codex; template/tooling không phải đóng góp mô hình. |
| Three.js | [mrdoob/three.js](https://github.com/mrdoob/three.js) | MIT | Tài liệu được tham khảo; dependency thực tế sẽ ghi sau G4. |
| FastAPI / Uvicorn | [FastAPI 0.164.0](https://pypi.org/project/fastapi/0.164.0/), [Uvicorn 0.54.0](https://pypi.org/project/uvicorn/0.54.0/) | MIT / BSD-3-Clause | API cục bộ. |
| React / Vite / TypeScript | [React và React DOM 19.3.1](https://github.com/facebook/react), [Vite 8.3.8](https://github.com/vitejs/vite), [TypeScript 5.9.3](https://github.com/microsoft/TypeScript) | MIT / MIT / Apache-2.0 | Giao diện, build và kiểm kiểu. |
| Playwright | [Playwright 1.65.1](https://github.com/microsoft/playwright) | Apache-2.0 | Kiểm thử Chromium. |
| PDF.js | [`pdfjs-dist` 6.5.438](https://github.com/mozilla/pdf.js), bản phân phối khóa trong `apps/web/package-lock.json` | [Apache-2.0](https://mozilla.github.io/pdf.js/) | Đọc lớp chữ của PDF cục bộ bằng worker. Vite tạo chunk tải lười và phục vụ worker từ cùng origin. |
| ReportLab / Noto Sans | [ReportLab 5.1.0](https://pypi.org/project/reportlab/5.1.0/), [Noto Sans](https://github.com/notofonts/NotoSans) từ bộ font Windows | BSD / SIL Open Font License 1.1 | Tạo PDF demo. File PDF chứa các ký tự font đã dùng. Web dùng tệp mẫu trực tiếp, generator chạy riêng. |

## Dữ liệu và trọng số

Trọng số `artifacts/model/model.crfsuite` do MedShield huấn luyện từ dữ liệu giả lập của dự án. [Metadata](artifacts/model/metadata.json) lưu cấu hình, lệnh train và SHA-256 của dữ liệu/trọng số. Các manifest trong `data/` ghi nguồn và số mẫu do người học trực tiếp rà soát.

- Lượt gán mù Meddies B dùng Qwen2.5-7B-Instruct Q4_K_M revision `bb5d59e06d9551d752d08b292a50eb208b07ab1f` (Apache-2.0), cục bộ. Đã kiểm SHA-256 hai shard GGUF `dfce12e3862a5283ccfb88221b48480e58745165de856439950d0f22590580db` và `539cf93f78e887edea1c04e2d7d8cdaca9d01dae9c9025bcb8accbe29df3d72a` và chạy thử trên CPU. [Nguồn trọng số chính thức](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/tree/bb5d59e06d9551d752d08b292a50eb208b07ab1f)
- Runtime lượt B là llama.cpp `b12754` Windows CPU x64 (MIT). SHA-256 ZIP `420e253581306c20c6ab349f4477640643b3711d607c31cb33a7e5ae580b3e71`. [Release chính thức](https://github.com/ggml-org/llama.cpp/releases/tag/b12754)
- VnCoreNLP 1.2 (`62bbc58fe5d113c898eae112656be97dcf50b3a0`, GPL-3.0-or-later) chạy thử cục bộ cho bước tách từ trên fixture giả lập. SHA-256 lần lượt của JAR, `vi-vocab` và `wordsegmenter.rdr` là `9e2811cdbc2ddfc71d04be5dc36e185c88dcd1ad4d5d69e4ff2e1369dccf7793`, `0a47c5b55bbce163029d37730a67b9479740388695c29c106c112b815613eaa5`, `9e62f96bd93e37a24f364238e8d8ae986fa5dad6dbc9f4eae622ab3651b7fa06`. [Nguồn VnCoreNLP đã ghim](https://github.com/vncorenlp/VnCoreNLP/tree/62bbc58fe5d113c898eae112656be97dcf50b3a0)

Tài liệu HTML so sánh và ZIP nghiên cứu người dùng cung cấp chỉ được đọc cục bộ; không đưa nguyên bộ slide SIC, dữ liệu n2c2 chưa được cấp quyền, clone upstream, virtualenv hoặc model chưa rõ quyền phân phối vào ZIP nộp.

## Việc phải hoàn tất trước G5

- Bổ sung phiên bản và giấy phép Three.js sau khi chốt dependency tại G4.
- Bổ sung license notices nếu sao chép phần mã đáng kể từ upstream. Hiện chưa sao chép source engine vào MedShield.
- Thay trạng thái chỉ khi smoke thật có bằng chứng; job CI skip không là chạy thành công.
