# ml/phase_q2_archive.py — Verify and rebuild the offset-only pre-Q2 prediction archive.
import json
from argparse import ArgumentParser
from collections.abc import Mapping, Sequence
from hashlib import sha256
from importlib import import_module, util
from pathlib import Path
from sys import modules
from typing import Any, cast

from apps.api.schemas import AnalyzeRequest, Mode
from ml.bio import Span
from ml.dataset import Note
from ml.evaluation_data import load_heldout
from ml.phase_q_benchmark import MODES, ROOT, Analyzer, _verify_frozen
from ml.phase_q_dataset import DATA_DIR, load_phase_q
from ml.scoring import score_documents

ARCHIVE = ROOT / "artifacts/phase-q-baseline-spans.json"
PRIOR_REPORT = ROOT / "artifacts/phase-q-comparison.json"
ARCHIVE_DIGEST = "300a6510b944c250721ae39d1fc36540b6644f4e1a7842dccda35f4362e3eed2"
SNAPSHOT_SOURCES = {
    "apps/api/adapters/vi_names_places.py": (
        "5b1d01ba8609d1593691f902342ce880f4c4a9827bf267cc0a6961e7146bd3dc"
    ),
    "apps/api/adapters/vi_structured.py": (
        "a3171672d5d82102a54c364d3e73e04c02618132a4a8f5ec0c33e57c8acb0c3c"
    ),
    "apps/api/adapters/rules.py": (
        "6e82a10c9cef9e5293280eeafa71e198aa057cd36c02f1b4d89b64f57debac20"
    ),
    "apps/api/services/hybrid.py": (
        "6d9d1b4ab5fa1a2d11da46d99cf58d0acd8c7c92e382edcd7475a4169d2d4765"
    ),
    "apps/api/services/analysis.py": (
        "aa3c245d39549298693ecaeec6aa91c4eaf25083a0fd2a43132f621fe5ec8e07"
    ),
}


def _sha256(data: bytes) -> str:
    """Hash UTF-8 content with canonical LF line endings for Windows checkout portability."""
    return sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def verify_archive() -> dict[str, Any]:
    """Load immutable historical predictions whose source hashes match the Phase Q record."""
    raw = ARCHIVE.read_bytes()
    result = json.loads(raw)
    if _sha256(raw) != ARCHIVE_DIGEST or result["source_sha256"] != SNAPSHOT_SOURCES:
        raise ValueError("Archive dự đoán Phase Q không khớp SHA-256.")
    return cast(dict[str, Any], result)


def load_archived_mode(
    set_name: str, notes: Sequence[Note], mode: Mode, archive: Mapping[str, Any]
) -> tuple[dict[str, list[Span]], dict[str, Any]]:
    """Check that decoded historical predictions reproduce the complete prior strict row."""
    item = archive["sets"][set_name][mode]
    predictions = {
        note_id: [Span(*span) for span in spans] for note_id, spans in item["by_note"].items()
    }
    strict = score_documents(notes, predictions, example_limit=5)
    rows = json.loads(PRIOR_REPORT.read_bytes())["sets"][set_name]["versions"]["after"]
    previous = next(row for row in rows if row["method"] == mode)
    examples = [
        {key: val for key, val in item.items() if key != "cause"} for item in previous["examples"]
    ]
    if any(previous[key] != value for key, value in strict.items() if key != "examples"):
        raise ValueError("Điểm strict của archive không khớp với báo cáo Phase Q.")
    if previous["engine"] != item["engine"] or examples != strict["examples"]:
        raise ValueError("Engine hoặc ví dụ strict không khớp với báo cáo Phase Q.")
    return predictions, item["engine"]


def capture(
    notes: Sequence[Note], mode: Mode, analyze: Analyzer
) -> tuple[dict[str, list[Span]], dict[str, Any]]:
    """Capture machine spans without input values and require a stable engine identity."""
    entities: dict[str, list[Span]] = {}
    engine = None
    for note in notes:
        response = analyze(AnalyzeRequest(text=note.text, language="vi", mode=mode))
        if engine is not None and response.engine != engine:
            raise ValueError("Engine thay đổi trong cùng một lượt đánh giá.")
        engine = response.engine
        entities[note.note_id] = [
            Span(item.start, item.end, item.label) for item in response.entities
        ]
    if (
        engine is None
        or engine.status != "available"
        or (engine.language, engine.mode) != ("vi", mode)
    ):
        raise ValueError("Engine đang đánh giá không khả dụng hoặc sai chế độ.")
    return entities, engine.model_dump(exclude_none=True)


def _load_snapshot(snapshot: Path) -> Analyzer:
    """Rebuild the checked Phase Q imports inside this dedicated CLI process."""
    for relative, expected in SNAPSHOT_SOURCES.items():
        if _sha256((snapshot / relative).read_bytes()) != expected:
            raise ValueError(f"Mã nguồn Phase Q sai SHA-256: {relative}")
    for relative in SNAPSHOT_SOURCES:
        name = relative.removesuffix(".py").replace("/", ".")
        parent, attr = name.rsplit(".", 1)
        package = import_module(parent)
        spec = util.spec_from_file_location(name, snapshot / relative)
        if spec is None or spec.loader is None:
            raise ValueError(f"Không thể nạp module Phase Q: {relative}")
        module = util.module_from_spec(spec)
        modules[name] = module
        setattr(package, attr, module)
        spec.loader.exec_module(module)
    return cast(Analyzer, vars(modules["apps.api.services.analysis"])["analyze_text"])


def main() -> None:
    """Recreate the pre-Q2 prediction archive from its exact local source snapshot."""
    parser = ArgumentParser(description="Tạo lại archive dự đoán trước Q2 từ mã đã kiểm SHA-256.")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    _verify_frozen()
    analyze = _load_snapshot(args.snapshot)
    sets: dict[str, Any] = {}
    for key, (notes, _) in {
        "original": load_heldout(DATA_DIR),
        "expanded": load_phase_q(),
    }.items():
        modes: dict[str, Any] = {}
        for mode in MODES:
            predictions, engine = capture(notes, mode, analyze)
            modes[mode] = {
                "engine": engine,
                "by_note": {
                    note_id: [[span.start, span.end, span.label] for span in spans]
                    for note_id, spans in predictions.items()
                },
            }
        sets[key] = modes
    result = {"source_sha256": SNAPSHOT_SOURCES, "sets": sets}
    output = (json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    if _sha256(output) != ARCHIVE_DIGEST:
        raise ValueError("Lượt chạy này không tái tạo đúng archive Phase Q.")
    with args.output.open("xb") as stream:
        stream.write(output)
    print(args.output)


if __name__ == "__main__":
    main()
