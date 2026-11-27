# Hướng dẫn gán nhãn MedShield

Trạng thái READY_FOR_REVIEW; BA sở hữu, QA và Research kiểm tra. Chỉ dùng ghi chú giả lập; mỗi mẫu là một ghi chú hoàn chỉnh, có thể có nhiều entity hoặc không có entity. Người học trực tiếp rà soát bao nhiêu mẫu phải ghi số thực tế, không gộp agent review thành human review.

## Ranh giới chung

Gán trên nguyên bản, không trim/normalize toàn ghi chú. Start bao gồm và end loại trừ, code point. Chỉ chọn giá trị định danh, không chọn từ dẫn (`bệnh nhân`, `sinh ngày`, `điện thoại`, `địa chỉ`, `mã`), khoảng trắng ngoài hoặc dấu câu kết thúc. Dấu nối/nối từ nằm trong giá trị thì giữ. Không có spans chồng nhau hoặc một đoạn mang nhiều nhãn. Nếu ngữ cảnh không đủ rõ, không tự suy diễn định danh từ mọi chuỗi số; lưu trường hợp khó để phân tích lỗi.

## Năm nhãn

| Nhãn | Phạm vi gán | Ví dụ chọn | Không chọn |
|---|---|---|---|
| NAME | Tên người bệnh, người thân/người liên hệ, nhân viên y tế/bác sĩ được nêu như cá nhân trong ghi chú | `Mai An`, `nguyễn minh hà`, `Trần Văn Bình` sau `BS.` | Chức danh BS./ông/bà; tên bệnh, thuốc, tổ chức, bệnh viện |
| DOB | Ngày/tháng/năm hoặc năm sinh khi được nêu rõ là sinh/ngày sinh/DOB; chỉ phần giá trị | `03/02/1995` sau `sinh ngày`; `1995` sau `năm sinh` | Ngày khám, ngày vào viện, tái khám, tuổi `29 tuổi`, mọi ngày không có ngữ cảnh sinh |
| PHONE | Số liên lạc cá nhân có ngữ cảnh điện thoại/liên hệ hoặc định dạng số điện thoại rõ | `0901234567`, `+84 901 234 567` | SpO2, liều thuốc, số đo, số thứ tự; không tự suy mọi chuỗi 10 chữ số thành số điện thoại khi trái ngữ cảnh |
| ID | Mã người bệnh/bệnh án định danh cá nhân; CCCD/CMND/hộ chiếu được ngữ cảnh nêu rõ | `BN-00071`, `HS-2048`, số sau `CCCD:` | Mã ICD/chẩn đoán `J06.9`, mã thuốc, mã phòng, số đo, ngày tháng |
| ADDR | Giá trị địa chỉ cư trú/liên lạc được ngữ cảnh xác nhận, gồm số nhà/đường/phường/quận/tỉnh liên tục | `12 đường Sen, phường Bình An, TP. Thủ Đức` | Từ dẫn `địa chỉ`; dấu chấm kết câu; địa danh chỉ nơi khám hoặc tên bệnh viện, không phải địa chỉ cá nhân |

Ngày sinh tiếng Anh theo `DOB`, `born`, `date of birth`; NAME vẫn gồm cá nhân theo phạm vi trên. Đối chứng upstream có thể không có nhãn tương đương: ghi rõ ánh xạ và đơn vị chấm thay vì gán nhãn phỏng đoán cho vùng che.

## Trường liên hệ và thông tin cần đính chính

- Nếu văn bản ghi rõ đây là số liên hệ, gán PHONE cho toàn bộ giá trị kể cả khi thiếu số hoặc ngoài dải đánh số. Nếu có nhãn máy lẻ rõ ràng, gán số máy lẻ thành vùng PHONE riêng và giữ từ dẫn ở ngoài cả hai vùng. Các cụm chữ số liền nhau qua khoảng trắng mà dài hơn dạng số thông thường cần được xét như một giá trị nguyên vẹn. Không gán riêng phần đầu nếu phần sau còn có thể thuộc cùng giá trị. Dấu phân cách trường hoặc từ dẫn như `mã giao dịch` bắt đầu giá trị khác. Với số đứng riêng, dùng ngữ cảnh để phân biệt số liên hệ với số kho, đơn vị đo và mã thiết bị.
- Khi ghi rõ đính chính ngày/năm sinh, gán từng giá trị cũ và mới thành hai vùng DOB. Cụm diễn đạt từ ngày sinh tới giá trị có thể chứa từ mô tả, tên người hoặc quan hệ. Ngày lập phiếu và ngày khám vẫn ở ngoài vùng. Gán giá trị được khẳng định là ngày sinh ngay cả khi ngày lịch không hợp lệ. Dấu phân tách ngày bị trộn là ca cần phân xử khi gán tay.
- Khi ghi rõ một trường định danh cá nhân, giữ giá trị ID ngay cả khi số định danh sai định dạng hoặc mâu thuẫn với ngày sinh. Kiểm tra lịch và định dạng giúp xếp ưu tiên đề xuất. Biên vàng dựa trên vai trò của giá trị trong văn bản.

Hướng dẫn này dùng cho dữ liệu mới. Manifest và biên vàng của các tập đã khóa tiếp tục theo revision lúc gán.

Khi ánh xạ nhãn nhà phát hành Meddies cho **train tạm**, `date` chỉ thành DOB nếu có neo sinh, năm sinh, ngày sinh, DOB hoặc born trong 48 code point quanh vùng. Phía trái chỉ xét trong cùng đoạn gần nhất sau dấu ngắt, bỏ nếu có ngày khác hoặc từ dẫn ngày khám/hẹn xen giữa. Phía phải chỉ chấp nhận nhãn DOB/ngày sinh/năm sinh đứng ngay sau giá trị. Cách lọc này chỉ phục vụ tạo nhãn train. Người gán validation/test áp dụng nghĩa của trường theo hướng dẫn chung. `company_name`, `email_address`, `private_url` và `secret` nằm ngoài năm nhãn hiện tại.

## Địa chỉ và dấu câu

ADDR bắt đầu ở ký tự đầu giá trị sau từ dẫn, kết thúc trước dấu phân cách chuyển sang thông tin khác hoặc dấu kết câu. Giữ dấu phẩy bên trong địa chỉ và dấu chấm viết tắt như `TP.`. Ví dụ `Địa chỉ: 12 đường Sen, phường Bình An, TP. Thủ Đức. Hẹn tái khám 18/12.` chọn đúng `12 đường Sen, phường Bình An, TP. Thủ Đức`. Nếu địa chỉ trải qua nhiều dòng nhưng vẫn cùng một giá trị liên tục, giữ newline trong span; nếu có mục nội dung khác xen giữa, dùng spans ADDR riêng.

## Ví dụ chuẩn

`Người bệnh Mai An, sinh ngày 03/02/1995, mã BN-00071. Hẹn khám lại 18/12.`

| start | end | label | slice |
|---|---|---|---|
| 11 | 17 | NAME | Mai An |
| 29 | 39 | DOB | 03/02/1995 |
| 44 | 52 | ID | BN-00071 |

Bản che: `Người bệnh [NAME_1], sinh ngày [DOB_1], mã [ID_1]. Hẹn khám lại 18/12.`

## Các ca khó bắt buộc

- Tên lặp: gán từng lần xuất hiện, cùng nhãn và chuỗi chính xác sinh cùng token. Khác viết hoa/thường hoặc dạng tổ hợp không tự coi tương đương.
- Emoji trước tên: emoji có một code point nhưng thường hai UTF-16 code units. Annotation dùng code point, UI chuyển đúng trước gửi API.
- Ký tự tổ hợp: không đổi `a` + dấu thành ký tự ghép sau khi gán; phải giữ offsets của nguyên bản.
- CRLF: giữ cả CR và LF nếu còn trong input; API tính mỗi ký tự là một code point. BOM đầu TXT được bỏ trước khi văn bản trở thành input chuẩn trên UI.
- Không có định danh: danh sách entities rỗng, vẫn là mẫu đánh giá hợp lệ; tránh loại bỏ để làm đẹp điểm.
- Ngày tái khám, ICD, chỉ số xét nghiệm và tên thuốc: thêm mẫu âm để đo che nhầm.
- Tên viết thường, bác sĩ/người thân, địa chỉ nhiều phần và ghi chú tự do: giữ trong test theo cùng chính sách.

## Dữ liệu và đánh giá

Chia train/validation/test theo họ mẫu câu trước khi sinh biến thể. Không để cùng template đổi tên/số xuất hiện hai split. QA giữ test khóa; Research chỉ chỉnh dựa train/validation. Mọi thay đổi nhãn phải có lý do annotation độc lập, revision và mở lại đánh giá; không sửa đáp án để đạt F1.

Chấm mỗi entity là tuple `(start,end,label)` chính xác, trước sửa tay. TP = giao hai tập, FP = dự đoán không khớp, FN = gold không khớp. Một span lệch ranh giới hoặc sai nhãn tạo một FP và một FN. Support = số gold từng nhãn. Khi support 0, hiển thị rõ; precision/recall/F1 dùng 0 cho mẫu số 0 và không gọi đó là thành công. Micro cộng TP/FP/FN trước tính điểm. Số ghi chú còn sót là số ghi chú có ít nhất một FN. Đánh giá vùng che của engine không có nhãn phải tách đơn vị riêng.
