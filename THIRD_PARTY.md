# Nguồn, phiên bản và giấy phép

Research/ML lập bản sơ bộ 18/11/2026 (Asia/Saigon), READY_FOR_REVIEW. Bảng phân biệt mã đã dùng với nguồn chỉ điều tra. Phiên bản cài thực tế cuối cùng lấy từ `uv.lock`, `apps/web/package-lock.json` và smoke artifacts; không suy ra đã chạy từ bảng này.

Cập nhật chuẩn bị môi trường trong G1: đã cài/import Presidio 2.2.366 và GEMINI pyDeid 1.0.1 exact SHA trong `.venv-upstream` Python 3.11.7; chưa có adapter/smoke suy luận MedShield. Đã tải/nạp `en_core_web_sm` 3.7.1 từ release chính thức spaCy (~12.2 MiB wheel; metadata model xác nhận MIT). Chi tiết pin tương thích và lỗi `pkg_resources` đã sửa nằm trong `docs/research.md`.

| Thành phần | Nguồn/revision kiểm tra | Giấy phép | Phạm vi/trạng thái hiện tại |
|---|---|---|---|
| Presidio Analyzer | [data-privacy-stack/presidio](https://github.com/data-privacy-stack/presidio/tree/9fc7774ed74faa0afd5ffb36da63e77b9a2f8c30), source version 2.2.366 | [MIT](https://github.com/data-privacy-stack/presidio/blob/9fc7774ed74faa0afd5ffb36da63e77b9a2f8c30/LICENSE) | Đã đọc source/metadata; chưa tích hợp/chưa smoke. Không lấy tên engine này gắn cho baseline tự viết. |
| Philter UCSF | [BCHSI/philter-ucsf](https://github.com/BCHSI/philter-ucsf/tree/4da3cf31c9bfbfd66c66b141c45ba7a47628dd0a) | [BSD-3-Clause](https://github.com/BCHSI/philter-ucsf/blob/4da3cf31c9bfbfd66c66b141c45ba7a47628dd0a/LICENSE) | Đã đọc source; chưa tích hợp/chưa smoke. Theo LICENSE repo, không dùng mô tả MIT trong bài báo thay LICENSE. Không tuyên bố chứng nhận UCSF áp dụng cho MedShield. |
| GEMINI pyDeid | [GEMINI-Medicine/pyDeid](https://github.com/GEMINI-Medicine/pyDeid/tree/f93d2ddb1fd857236b2d3b4b761af2b8028c7281), setup version 1.0.1 | [MIT](https://github.com/GEMINI-Medicine/pyDeid/blob/f93d2ddb1fd857236b2d3b4b761af2b8028c7281/LICENSE.md) | Đã đọc source; chưa tích hợp/chưa smoke. Cài đúng git URL+SHA, không nhầm gói trùng tên. Không xuất mapping gốc. |
| sklearn-crfsuite | [scrapinghub/sklearn-crfsuite](https://github.com/scrapinghub/sklearn-crfsuite), HEAD tham khảo e18a02ae11b61f703c0ec460c44cfdd90db00591 | MIT (cần đối chiếu metadata bản đã cài khi khóa) | Dependency dự kiến cho mô hình BIO CRF do dự án huấn luyện, không phải model pretrained bên ngoài. |
| GitHub Spec Kit | [github/spec-kit](https://github.com/github/spec-kit/tree/59d61c59630c3bd5a294f4c23e43a60d8ab98d02), CLI 1.4.3.dev0 | MIT | Tech Lead đã scaffold integration Codex; template/tooling không phải đóng góp mô hình. |
| Three.js | [mrdoob/three.js](https://github.com/mrdoob/three.js) | MIT | Tài liệu được tham khảo; dependency thực tế sẽ ghi sau G4. |

## Dữ liệu và trọng số

Dữ liệu mới sẽ là ghi chú **giả lập do agent tạo**, nguồn/quyền chia sẻ và số người học trực tiếp rà soát phải ghi trong data card. Không có hồ sơ bệnh nhân thật. Chưa có trọng số mô hình mới tại G0. Khi có mô hình dự án huấn luyện, phải ghi lệnh train, cấu hình, dữ liệu/hash và hash trọng số; không gán nguồn pretrained cho mô hình tự train.

Tài liệu HTML so sánh và ZIP nghiên cứu người dùng cung cấp chỉ được đọc cục bộ; không đưa nguyên bộ slide SIC, dữ liệu n2c2 chưa được cấp quyền, clone upstream, virtualenv hoặc model chưa rõ quyền phân phối vào ZIP nộp.

## Việc phải hoàn tất trước G5

- Bổ sung phiên bản và giấy phép từ metadata của toàn bộ dependency trực tiếp FastAPI/Uvicorn/React/TypeScript/Vite, CRF và Three.js thực tế đã cài.
- Bổ sung license notices nếu sao chép phần mã đáng kể từ upstream. Hiện chưa sao chép source engine vào MedShield.
- Ghi rõ phiên bản/nguồn/license model spaCy nếu adapter sử dụng; dependency library và model có thể có license khác nhau.
- Thay trạng thái chỉ khi smoke thật có bằng chứng; job CI skip không là chạy thành công.
