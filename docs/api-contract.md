# Hợp đồng API MedShield v1

Trạng thái: READY_FOR_REVIEW; BA soạn, Dev và QA review. Base local dự kiến `http://127.0.0.1:8000`; cấu hình thực tế do DevOps xác nhận. JSON UTF-8; không có session server hoặc lưu lịch sử input.

## Kiểu dùng chung

`Label = "NAME" | "DOB" | "PHONE" | "ID" | "ADDR"`.

```ts
type Entity = {
  start: number;
  end: number;
  label: Label;
  source: string;
  score: number;
};
type Engine = {
  name: string;
  status: "available" | "unavailable";
  mode: "rules" | "ner" | "hybrid";
  language: "vi" | "en";
  version?: string;
  model_revision?: string;
};
type Metadata = {
  entity_count: number;
  counts_by_label: Record<Label, number>;
  offset_unit: "unicode_code_point";
};
```

`source` mô tả adapter/quy tắc thực sự tạo phát hiện; kết hợp nguồn có thể nối bằng `+`, không chứa input. `score` hữu hạn trong [0,1], không đồng nghĩa xác suất đã hiệu chuẩn. Entity thủ công dùng `manual`, score 1. Response không cần thêm chuỗi gốc vì UI lấy substring từ input trong bộ nhớ.

Offset là code point, khoảng `[start,end)`, bắt buộc số nguyên nghiêm ngặt (không bool), `0 <= start < end <= len(text)`. Python dùng slice trực tiếp; trình duyệt dùng `Array.from(text)` để cắt theo code point hoặc chuyển từ UTF-16 selection bằng số code point trước ranh giới. Không cho ranh giới cắt đôi surrogate pair. Dấu tổ hợp giữ nguyên nhiều code point; không NFC/NFD-normalize trước/sau suy luận nếu không có ánh xạ ngược.

Text từ 1 tới 50.000 code point và có ký tự ngoài whitespace; tối đa 2.000 entity. Trường không được định nghĩa bị từ chối. Endpoint redact yêu cầu spans không chồng nhau, kể cả span trùng; cho phép hai span tiếp giáp. Service sắp xếp theo start trước khi thay thế. Analyze phải giải quyết xung đột trước khi trả danh sách không chồng nhau và công bố ưu tiên trong tài liệu engine.

## GET /health

HTTP 200 khi API đang phục vụ. Không suy diễn API sống đồng nghĩa mọi engine sẵn sàng.

```json
{
  "status": "ok",
  "engines": [
    {"name": "medshield-rules", "status": "available", "mode": "rules", "language": "vi"},
    {"name": "medshield-ner", "status": "unavailable", "mode": "ner", "language": "vi"}
  ]
}
```

Các adapter upstream được bổ sung với tên/trạng thái đúng thực tế; lý do an toàn có thể thêm `reason`, không chứa đường dẫn nhạy cảm, input hoặc stack trace. Chi tiết revision và lệnh smoke nằm trong báo cáo môi trường/THIRD_PARTY.

## POST /api/analyze

Request có ba trường bắt buộc: text, language (`vi` hoặc `en`), mode (`rules`, `ner`, `hybrid`). Không tự đổi mode khi engine yêu cầu không hoạt động; trả 503.

```json
{"text":"Người bệnh Mai An, sinh ngày 03/02/1995, mã BN-00071. Hẹn khám lại 18/12.","language":"vi","mode":"rules"}
```

HTTP 200 ví dụ hợp lệ (score/source của engine thực tế có thể khác):

```json
{
  "entities": [
    {"start":11,"end":17,"label":"NAME","source":"medshield-rules","score":0.8},
    {"start":29,"end":39,"label":"DOB","source":"medshield-rules","score":0.95},
    {"start":44,"end":52,"label":"ID","source":"medshield-rules","score":0.95}
  ],
  "redacted_text":"Người bệnh [NAME_1], sinh ngày [DOB_1], mã [ID_1]. Hẹn khám lại 18/12.",
  "engine":{"name":"medshield-rules","status":"available","mode":"rules","language":"vi"}
}
```

Phản hồi chứa entities tự động trước sửa tay; không dùng kết quả sửa tay để chấm mô hình. Không đưa request text vào engine metadata. Frontend phải kiểm tra phiên bản input/request trước áp dụng response.

## POST /api/redact

Nhận input hiện hành và danh sách entities hiện hành, không tự phân tích lại. Có thể truyền `entities: []` để giữ nguyên text sau quyết định người dùng.

```json
{
  "text":"Người bệnh Mai An, sinh ngày 03/02/1995, mã BN-00071. Hẹn khám lại 18/12.",
  "entities":[
    {"start":11,"end":17,"label":"NAME","source":"manual","score":1},
    {"start":29,"end":39,"label":"DOB","source":"medshield-rules","score":0.95},
    {"start":44,"end":52,"label":"ID","source":"medshield-rules","score":0.95}
  ]
}
```

HTTP 200:

```json
{
  "redacted_text":"Người bệnh [NAME_1], sinh ngày [DOB_1], mã [ID_1]. Hẹn khám lại 18/12.",
  "metadata":{
    "entity_count":3,
    "counts_by_label":{"NAME":1,"DOB":1,"PHONE":0,"ID":1,"ADDR":0},
    "offset_unit":"unicode_code_point"
  }
}
```

`entity_count` và counts đếm số spans, không phải số token duy nhất. Token bắt đầu từ 1 riêng mỗi nhãn, theo thứ tự xuất hiện. Khóa tái sử dụng token là `(label, chuỗi slice chính xác)`; cùng tên có cùng token khi cả hai spans đã được chọn, không tự phát hiện thêm lần lặp. Đếm lại từ đầu trên mỗi request/tài liệu. Chuỗi ngoài spans không bị sửa; không phát hành bản đồ tên-token.

UI không cho tải trước xác nhận. Xác nhận không được server lưu; API redact tạo preview theo danh sách đã gửi. JSON tải xuống có đúng hai trường của response này, không kèm entities/input. Vì người dùng có thể chủ động bỏ span, bản xuất giữ đoạn đó theo quyết định của họ; phải rà soát đầy đủ trước xác nhận.

## GET /api/evaluation

Không có artifact hợp lệ: HTTP 200 `{"status":"unavailable","reason":"Chưa có kết quả đánh giá."}`. Có artifact: HTTP 200 `{"status":"available","evaluation":{...}}`. Đọc artifact được script đánh giá tạo, không suy luận hoặc sửa điểm trong endpoint.

Artifact tối thiểu lưu: schema version, ngày chạy UTC, seed, dataset revision/hash, split và family IDs, provenance/số người học rà soát, model/package revision và config, lệnh tái tạo, results phân theo language/method, số notes/entities, TP/FP/FN/precision/recall/F1/support từng nhãn và micro, số notes còn FN, ví dụ FP/FN giả lập. Đơn vị `exact_span_label` hoặc `redaction_region` phải rõ; không so sánh trực tiếp hai đơn vị khác nhau. Nếu engine chưa chạy, lưu status/reason và command tái hiện, không điền điểm bằng 0 thay kết quả chưa có.

## Lỗi an toàn

Mọi lỗi JSON API có envelope duy nhất:

```json
{"error":{"code":"VALIDATION_ERROR","message":"Dữ liệu yêu cầu không hợp lệ."}}
```

| HTTP | code | Khi nào |
|---|---|---|
| 422 | VALIDATION_ERROR | JSON hỏng, thiếu/sai kiểu/trường lạ, text trống/quá dài, nhãn hoặc score không hợp lệ, spans quá nhiều |
| 422 | INVALID_SPAN | Span âm, rỗng, quá text hoặc chồng lấn |
| 503 | ENGINE_UNAVAILABLE | Engine/ngôn ngữ/chế độ yêu cầu không sẵn sàng |
| 500 | INTERNAL_ERROR | Lỗi chưa dự kiến; thông báo chung an toàn |

Không trả Pydantic `input`, nội dung request, chuỗi entity hoặc stack trace trong lỗi. Không ghi request body trong access/error logs. JSON malformed và lỗi validation cũng phải dùng envelope này. Không expose exception string từ engine cho người dùng. CORS chỉ cho frontend local được cấu hình; JSON response không cache input.
