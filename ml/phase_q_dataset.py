# ml/phase_q_dataset.py — Generate and verify the separate synthetic Phase Q evaluation corpus.
import json
import random
from collections import Counter
from hashlib import sha256
from pathlib import Path
from string import Formatter
from typing import Any
from unicodedata import normalize

from ml.dataset import MANIFEST_FILENAME, Note, parse_note
from ml.evaluation_data import TEST_MANIFEST_FILENAME, read_object

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CORPUS = "phase-q-test.jsonl"
MANIFEST = "phase-q-test-manifest.json"
SEED = 20261125
REVISION = "vi-phase-q-heldout-v1"

# The structure and field order were authored before any scoring on the new corpus.
FAMILIES = {
    "q-insurance-reconciliation": (
        "Đối soát bảo hiểm, phiếu {REF}. Hồ sơ mang tên {NAME}; "
        "số thẻ BHYT: {INSURANCE}. Năm sinh trên sổ: {DOB_YEAR}. "
        "Liên hệ người giữ thẻ qua {PHONE}. Nơi gửi giấy: {ADDR}."
    ),
    "q-dietary-delivery": (
        "🗒 Phiếu chuyển suất ăn {REF}\nGiao tận nhà cho {NAME} ở {ADDR}\n"
        "Dặn gọi số {PHONE} lúc đến. Mã BN: {CHART}. Khẩu phần 1.800 kcal."
    ),
    "q-occupational-intake": (
        "Sàng lọc nghề nghiệp {REF}: tên người đến khám là {NAME}. "
        "Sinh {DOB_WORDS}; khai số CMND {CMND} và điện thoại {PHONE_DOTS}. "
        "Ngày khám 16/05/2025."
    ),
    "q-witness-statement": (
        "Xác nhận bàn giao tài sản {REF}. Người làm chứng, chị {NAME_LOWER}, "
        "để lại địa chỉ liên lạc {ADDR} và số di động {PHONE_INTL}. "
        "Người nhận ký thay là {OTHER_NAME}. Không có tiền mặt."
    ),
    "q-audiology-sticker": (
        "Phiếu đo thính lực {REF}\r\n"
        "HỌ VÀ TÊN: {NAME_UPPER}\r\nSN: {DOB_ISO}\r\n"
        "Số hồ sơ: {CHART}\r\nĐT: {PHONE_DASH}\r\nTai trái 30 dB."
    ),
    "q-outreach-routing": (
        "Bàn giao tuyến xe số {REF}. Tài xế đón {NAME} ở {ADDR_SHORT}; "
        "liên lạc qua {PHONE_INTL_PAREN}. PID {CHART}. "
        "Nhắc có mặt trước 08:30, ngày 01/04/2025."
    ),
    "q-specimen-form-signoff": (
        "Phiếu đồng ý lưu mẫu {REF}. Tôi, {NAME}, đồng ý hủy mẫu sau 7 ngày. "
        "CCCD: {CCCD}; ngày sinh {DOB_DMY}. BS. {OTHER_NAME} chứng kiến; "
        "có thể gọi lại {PHONE} để rút đồng ý."
    ),
    "q-prescription-return": (
        "Yêu cầu nhận lại đơn thuốc {REF}. Ông {NAME} dặn gửi đơn về {ADDR}. "
        "Để đối chiếu, đọc mã HS {CHART} hoặc gọi điện cho ông qua {PHONE_FIXED}. "
        "Đơn chứa vitamin D, 800 IU mỗi ngày."
    ),
    "q-radiology-correction": (
        "Đính chính tiêu đề phim số {REF}: ghi đúng họ tên {NAME_NFD}; "
        "thay số hộ chiếu thành {PASSPORT}. Trên bìa có ngày sinh {DOB_SHORT}; "
        "địa chỉ thường trú {ADDR}, bỏ dòng cũ."
    ),
    "q-discharge-voice-transcript": (
        "Bản chép lời ra viện {REF}: '{NAME_LOWER} đây ạ, tôi sinh năm {DOB_YEAR}. "
        "Số tôi đang dùng {PHONE_SPACES}. Vâng, {NAME_LOWER} sẽ quay lại vào 18/12.'"
    ),
    "q-transfer-bilingual-card": (
        "Thẻ trung chuyển {REF} | Patient name: {NAME} | DOB: {DOB_DOTS} | "
        "Liên hệ: {PHONE_DASH} | Đ/c: {ADDR_SHORT} | Mã hồ sơ: {CHART}."
    ),
    "q-mobile-form-ascii": (
        "Dong bo bieu mau {REF}: Ho ten: {NAME_ASCII}; "
        "Ngay sinh: {DOB_DMY}; So dien thoai: {PHONE}; Thuong tru: {ADDR_ASCII}; "
        "ma ho so: {CHART}."
    ),
    "q-counselor-followup": (
        "Kế hoạch hỗ trợ {REF}. Người được tư vấn {NAME} đề nghị gọi mẹ {OTHER_NAME} "
        "theo số {PHONE}. Hai người đăng ký nhận thư tại {ADDR}; "
        "buổi sau là 13/07/2025."
    ),
    "q-medication-equipment-control": (
        "Nhật ký kiểm định {REF}: vật tư lô 0900000041, mã ICD J06.9, "
        "máy theo dõi 093-000-0042. SpO2 96%, 500 mg mỗi 8 giờ. "
        "Bảo trì 31/08/2025, tại Bệnh viện Mầm Trăng."
    ),
    "q-bed-queue-control": (
        "Bảng điều phối phòng {REF}: mã giường BN-0087, "
        "thay băng lúc 16:40, ngày khám 22.04.2025. "
        "Khối lượng kiểm kê 079202000001 đơn vị; chưa có thông tin liên hệ."
    ),
}

NAMES = (
    "Đinh Mộc Vân",
    "Đoàn An Nguyệt",
    "Cao Bảo Triều",
    "Mai Lạc Hương",
    "Hồ Thiên Lý",
    "Vũ Châu Sa",
    "Dương Nhật Vỹ",
    "Tạ Bích Lam",
    "Trần Hải Nhiên",
    "Phạm Hạ Thi",
    "Nguyễn Sương Tùng",
    "Lê Hà Miên",
    "Bùi Thụy Yến",
    "Đặng Uyển Nhi",
    "Đào Anh Khuê",
)
STREETS = (
    "Hoa Vân Giấy",
    "Gió Bờ Lau",
    "Vườn Cánh Diều",
    "Trăng Qua Suối",
    "Vệt Lá Cọ",
    "Thềm Ngọc Mây",
    "Bóng Hoàng Hôn",
    "Mầm Ngô Non",
    "Nhánh Giọt Sương",
)
PREFIXES = ("032", "038", "056", "058", "070", "077", "082", "088", "091", "096")


def _ascii(text: str) -> str:
    """Return the unaccented surface form for a deliberately unaccented record."""
    return "".join(c for c in normalize("NFD", text) if not "\u0300" <= c <= "\u036f").translate(
        str.maketrans("Đđ", "Dd")
    )


def _values(index: int, rng: random.Random) -> dict[str, tuple[str, str]]:
    """Build independent fictional fields and associate each slot with its gold label."""
    name, other_name = rng.sample(NAMES, 2)
    street = rng.choice(STREETS)
    addr = f"{index + 2} đường {street}, phường Mầm Trăng, TP. Cánh Diều"
    local = rng.choice(PREFIXES) + f"000{index + 1:04d}"
    first, middle, last = local[:3], local[3:6], local[6:]
    day, month, year = rng.randint(1, 28), rng.randint(1, 12), rng.randint(1950, 2004)
    century_gender = (year // 100 - 19) * 2 + index % 2

    return {
        "REF": (f"Q-{index + 1:03d}", ""),
        "NAME": (name, "NAME"),
        "OTHER_NAME": (other_name, "NAME"),
        "NAME_LOWER": (name.lower(), "NAME"),
        "NAME_UPPER": (name.upper(), "NAME"),
        "NAME_NFD": (normalize("NFD", name), "NAME"),
        "NAME_ASCII": (_ascii(name), "NAME"),
        "ADDR": (addr, "ADDR"),
        "ADDR_SHORT": (f"{index + 2}/4 ngõ {street}, P. Mầm Trăng, Q. Cánh Diều", "ADDR"),
        "ADDR_ASCII": (_ascii(addr), "ADDR"),
        "PHONE": (local, "PHONE"),
        "PHONE_SPACES": (f"{first} {middle} {last}", "PHONE"),
        "PHONE_DOTS": (f"{first}.{middle}.{last}", "PHONE"),
        "PHONE_DASH": (f"{first}-{middle}-{last}", "PHONE"),
        "PHONE_INTL": (f"+84 {first[1:]} {middle} {last}", "PHONE"),
        "PHONE_INTL_PAREN": (f"(+84) {first[1:]} {middle} {last}", "PHONE"),
        "PHONE_FIXED": (f"024 0000 {index + 1:04d}", "PHONE"),
        "CCCD": (f"001{century_gender}{year % 100:02d}{index + 1:06d}", "ID"),
        "CMND": (f"001{index + 1:06d}", "ID"),
        "PASSPORT": (f"P{index + 1:07d}", "ID"),
        "INSURANCE": (f"DN401{index + 1:010d}", "ID"),
        "CHART": (f"{rng.choice(('BA', 'KH', 'MS'))}-{index + 1:04d}/Q", "ID"),
        "DOB_DMY": (f"{day:02d}/{month:02d}/{year}", "DOB"),
        "DOB_SHORT": (f"{day:02d}-{month:02d}-{year % 100:02d}", "DOB"),
        "DOB_DOTS": (f"{day:02d}.{month:02d}.{year}", "DOB"),
        "DOB_ISO": (f"{year}-{month:02d}-{day:02d}", "DOB"),
        "DOB_YEAR": (str(year), "DOB"),
        "DOB_WORDS": (f"ngày {day} tháng {month} năm {year}", "DOB"),
    }


def _record(index: int, family: str, template: str, rng: random.Random) -> dict[str, Any]:
    """Render one template and build offsets directly on its original code points."""
    values = _values(index, rng)
    text = ""
    entities = []
    for literal, field, _, _ in Formatter().parse(template):
        text += literal
        if field is not None:
            value, label = values[field]
            if label:
                entities.append(
                    {"start": len(text), "end": len(text) + len(value), "label": label}
                )
            text += value
    return {
        "note_id": f"vi-phase-q-{index + 1:03d}",
        "family_id": family,
        "text": text,
        "entities": entities,
    }


def _json(data: object) -> str:
    """Encode one Unicode JSON record without escaping code points."""
    return json.dumps(data, ensure_ascii=False)


def generate(data_dir: Path = DATA_DIR) -> None:
    """Create the corpus and manifest once without overwriting any existing split."""
    corpus_path, manifest_path = data_dir / CORPUS, data_dir / MANIFEST
    if corpus_path.exists() or manifest_path.exists():
        raise FileExistsError("Tập Phase Q đã khóa. Dùng thư mục trống để tái tạo.")
    rng = random.Random(SEED)
    source = [
        _record(family_index * 10 + variant, family, template, rng)
        for family_index, (family, template) in enumerate(FAMILIES.items())
        for variant in range(10)
    ]
    raw = ("\n".join(map(_json, source)) + "\n").encode("utf-8")
    notes = [parse_note(record) for record in source]
    manifest = {
        "schema_version": 1,
        "dataset_revision": REVISION,
        "path": f"data/{CORPUS}",
        "split": "heldout_phase_q",
        "language": "vi",
        "synthetic": True,
        "provenance": "Agent Research/BA (Codex) soạn họ mẫu và gán nhãn trường giả lập. "
        "Không dùng bệnh án, dữ liệu công khai hay thông tin định danh được thu thập.",
        "participant_reviewed_count": 0,
        "annotation_review": "Chưa được con người gán đôi hoặc rà soát.",
        "contact_values": "Số giả lập để kiểm mẫu hình, không gọi điện hay tra cứu danh tính.",
        "seed": SEED,
        "offset_unit": "unicode_code_point",
        "note_count": len(notes),
        "gold_entities": dict(
            sorted(Counter(span.label for n in notes for span in n.entities).items())
        ),
        "families": {
            family: [n.note_id for n in notes if n.family_id == family] for family in FAMILIES
        },
        "digest": {
            "algorithm": "sha256",
            "canonicalization": "UTF-8/LF",
            "value": sha256(raw).hexdigest(),
        },
    }
    data_dir.mkdir(parents=True, exist_ok=True)
    with corpus_path.open("xb") as output:
        output.write(raw)
    with manifest_path.open("xb") as output:
        output.write((json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def load_phase_q(data_dir: Path = DATA_DIR) -> tuple[list[Note], dict[str, Any]]:
    """Read the frozen Phase Q corpus after verifying digest, support and disjoint families."""
    manifest = read_object(data_dir / MANIFEST)
    raw = (data_dir / CORPUS).read_bytes().replace(b"\r\n", b"\n")
    if (
        manifest["dataset_revision"] != REVISION
        or manifest["digest"]["value"] != sha256(raw).hexdigest()
        or not raw.endswith(b"\n")
    ):
        raise ValueError("SHA-256 hoặc revision tập Phase Q không khớp.")
    notes = [parse_note(json.loads(line)) for line in raw.decode("utf-8").split("\n")[:-1]]
    families: dict[str, list[str]] = {}
    for note in notes:
        families.setdefault(note.family_id, []).append(note.note_id)
    development = read_object(DATA_DIR / MANIFEST_FILENAME)
    old_test = read_object(DATA_DIR / TEST_MANIFEST_FILENAME)
    previous_families = {
        family for split in development["splits"].values() for family in split["family_ids"]
    } | {family["family_id"] for family in old_test["families"]}
    support = Counter(span.label for note in notes for span in note.entities)
    if (
        manifest["families"] != families
        or set(families) & previous_families
        or manifest["note_count"] != len(notes)
        or manifest["gold_entities"] != support
        or len({note.note_id for note in notes}) != len(notes)
        or len({note.text for note in notes}) != len(notes)
    ):
        raise ValueError("Tập Phase Q có lỗi họ mẫu, số ghi chú hoặc số vùng vàng.")
    return notes, manifest


if __name__ == "__main__":
    generate()
