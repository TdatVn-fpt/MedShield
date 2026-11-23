# ml/data_families.py — Define separate train and validation families and synthetic values.

TRAIN_FAMILIES = {
    "tr-intake-fields": (
        "Phiếu tiếp nhận\r\nHọ và tên: {patient}\r\nNgày sinh: {birth}\r\n"
        "Điện thoại: {phone}\r\nĐịa chỉ: {address}.\r\n{symptom}"
    ),
    "tr-narrative-history": (
        "Trong phần hỏi bệnh, chị {patient} cho biết {complaint}. Cấp mã bệnh án {record}."
    ),
    "tr-contact-person": (
        "Liên hệ khi cần qua {relative}, người nhà của {patient}, số {phone}. {symptom}"
    ),
    "tr-clinician-signature": ("{symptom} Dặn theo dõi tại nhà. Người ghi phiếu: BS. {doctor}."),
    "tr-lowercase-midline": (
        "Lúc bàn giao, người bệnh {midline_patient} vẫn tỉnh; sinh năm {birth_year}. {symptom}"
    ),
    "tr-residence-block": ("Nơi cư trú hiện tại của bệnh nhân: {address}. Khoa Nội đã tiếp nhận."),
    "tr-multiline-delivery": (
        "Địa chỉ nhận giấy hẹn:\r\n{multiline_address}.\r\nCăn dặn đem theo kết quả xét nghiệm."
    ),
    "tr-identity-check": (
        "Xác minh hồ sơ {record} bằng số CCCD {citizen}, sau đó kiểm ngày sinh "
        "{birth} và số điện thoại {phone}."
    ),
    "tr-appointment-negative": (
        "Tái khám ngày {appointment} tại Khoa Nội, lấy số thứ tự {queue}. {symptom}"
    ),
    "tr-measurement-negative": (
        "Mã ICD {icd}; SpO2 {oxygen}%, liều {dose} mg. Mẫu xét nghiệm đạt."
    ),
}

VALIDATION_FAMILIES = {
    "va-call-chronology": (
        "Đầu cuộc gọi hỏi lịch khám. Sau khi nghe hướng dẫn, người gọi xưng là "
        "{patient}, xác nhận sinh ngày {birth} và hẹn gọi lại qua số {phone}."
    ),
    "va-handover-repeat": (
        "🙂 Chuyển ca cho BS. {doctor} theo dõi {patient}. "
        "Khi gọi vào phòng, {patient} báo {complaint}."
    ),
    "va-address-change": (
        "Chỉnh nơi gửi thư: bỏ địa chỉ cũ {old_address}; "
        "địa chỉ liên lạc mới là {address}, xin cập nhật hồ sơ {record}."
    ),
    "va-followup-negative": (
        "Ngày uống thuốc cuối {appointment}, liều {dose} mg; "
        "sau 2 ngày đo lại SpO2 (hiện {oxygen}%) và mang kết quả tới phòng {queue}."
    ),
}

TRAIN_NAMES = (
    "Trần Lam",
    "Phạm An Thư",
    "Lưu Kha",
    "Nguyễn Thanh Miên",
    "Đỗ Lạc",
    "Vũ Hoài Trúc",
    "Bùi Linh Hạ Diệp",
    "Dương Quỳnh Khôi",
    "Hồ Liễu",
    "Tạ Hải Sơn",
    "Lê Thảo Ngân",
    "Võ Thu Gia Hân",
)
VALIDATION_NAMES = (
    "Mai Tuyết Bình",
    "Hoàng Nhật Khánh",
    "Cao Hương Vi",
    "Hà Quang Đăng",
    "Tô Bảo Vy",
    "Đặng Tiểu Lâm",
    "Phan Anh Tú",
    "Ninh Uyển Chi",
)
TRAIN_STREETS = ("Hoa Chàm", "Gió Sớm", "Trúc Ngà", "Cỏ May", "Bờ Sim", "Hạt Mưa")
VALIDATION_STREETS = ("Mây Hồng", "Bến Nguyệt", "Sương Mai", "Đồi Mộc", "Lá Bạc")
WARD_NAMES = ("Bình Vân", "Thanh Mộc", "An Lưu", "Quỳnh Giang", "Phù Dương", "Trúc Khê")
CITY_NAMES = ("Lam Viên", "Vân Phố", "Hạ Tùng", "Tân Mây", "Thạch Liên", "Nam Trúc")
COMPLAINTS = (
    "ho khan nhẹ",
    "ngủ kém hai đêm",
    "đau đầu về chiều",
    "đã giảm chóng mặt",
    "thấy mỏi vai",
    "ăn uống bình thường",
)
ICD_CODES = ("J06.9", "R05", "R51", "M54.9", "R42", "R53")
