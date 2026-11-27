# ml/phase_e_sampling.py — Verify that sealed gold uses the preregistered blind sample.
from collections.abc import Mapping
from hashlib import sha256

from ml.phase_e_annotation import _manifest, read_source
from ml.phase_e_intake import IntakeError, Record, _read_payload


def validate_sampling(
    source_blob: bytes,
    packet_blob: bytes,
    expected_packet_sha256: str,
    gold: Mapping[str, Record],
) -> set[str]:
    """Verify the QA recorded packet digest, source metadata and exact sampled note IDs."""
    if sha256(packet_blob).hexdigest() != expected_packet_sha256:
        raise IntakeError("SHA-256 manifest mẫu không khớp giá trị QA ghi trước khi gán.")
    notes = read_source(source_blob)
    packet = _read_payload(packet_blob, "packet-manifest.json")
    if (
        not isinstance(packet, dict)
        or type(packet.get("seed")) is not int
        or packet != _manifest(source_blob, notes, packet["seed"])
    ):
        raise IntakeError("Không tái tạo được mẫu gán đôi từ nguồn đã đăng ký.")
    if notes.keys() != gold.keys():
        raise IntakeError("Danh sách ghi chú vàng khác nguồn lấy mẫu.")
    for key, record in gold.items():
        note = notes[key]
        if (
            record.note.text != note.note.text
            or record.note.family_id != note.note.family_id
            or record.patient_group != note.patient_group
            or record.slices != frozenset(note.slices)
        ):
            raise IntakeError("Văn bản, nhóm hoặc lát của tập vàng khác nguồn lấy mẫu.")
    return set(packet["double_note_ids"])
