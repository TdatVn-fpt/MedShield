# ml/phase_e_groups.py — Check Phase E group separation before and after annotation.
from collections.abc import Iterable

from ml.phase_e_types import IntakeError

GroupPair = tuple[str, str]


def check_groups(splits: Iterable[Iterable[GroupPair]]) -> None:
    """Require every patient and family to occur in only one split."""
    seen_patients: set[str] = set()
    seen_families: set[str] = set()
    for pairs in splits:
        pairs_set = set(pairs)
        patients = {patient for patient, _ in pairs_set}
        families = {family for _, family in pairs_set}
        if patients & seen_patients or families & seen_families:
            raise IntakeError("Nhóm bệnh nhân hoặc họ mẫu trùng giữa các split.")
        seen_patients |= patients
        seen_families |= families
