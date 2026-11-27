# ml/meddies_offset_grammar.py — Constrain blind Qwen quotations to exact source offsets.
import json
from typing import Any

from ml.bio import GOLD_LABELS
from ml.dataset import parse_note
from ml.phase_e_types import IntakeError

OFFSET_INSTRUCTION = (
    "\nFor this output use objects with exactly these keys in this order: label, start, value. "
    "start is the zero-based Unicode code point index of the first character "
    "in the original note. "
    "Use the original note without normalization. Return all spans for the same five categories.\n"
)


def render_qwen_chat(prompt: str, note: str) -> str:
    """Render the pinned Qwen ChatML template without trimming note or prompt."""
    return (
        f"<|im_start|>system\n{prompt}<|im_end|>\n"
        f"<|im_start|>user\n{note}<|im_end|>\n"
        "<|im_start|>assistant\n"
    )


def _literal(value: str) -> str:
    """Quote one literal in GBNF, retaining Unicode code points."""
    return json.dumps(value, ensure_ascii=False)


def source_offset_grammar(note: str) -> str:
    """Generate all contiguous nonblank-trimmed source spans, coupled to their start position."""
    source = note.rstrip()
    if not source:
        raise IntakeError("Văn bản rỗng không tạo được ngữ pháp thử lại.")
    choices = " | ".join(f"p{i}" for i, char in enumerate(source) if not char.isspace())
    rules = [
        'root ::= "{" ws '
        + _literal('"entities"')
        + ' ws ":" ws "[" ws (region ("," ws region)*)? "]" ws "}"',
        'region ::= "{" ws '
        + _literal('"label"')
        + ' ws ":" ws label ws "," ws '
        + _literal('"start"')
        + ' ws ":" ws position ws "}" ws',
        "label ::= " + " | ".join(_literal(_literal(label)) for label in GOLD_LABELS),
        f"position ::= {choices}",
        r"ws ::= [ \t\r\n]?",
    ]
    quote = _literal('"')
    value_key = _literal('"value"')
    for position, char in enumerate(source):
        continuation = ""
        if position + 1 < len(source):
            suffix = f" q{position + 1}"
            continuation = suffix if char.isspace() else suffix + "?"
        rules.append(f"q{position} ::= {_literal(_literal(char)[1:-1])}{continuation}")
        if not char.isspace():
            rules.append(
                f'p{position} ::= {_literal(str(position))} ws "," ws {value_key} '
                f'ws ":" ws {quote} q{position} {quote}'
            )
    return "\n".join(rules) + "\n"


def source_offset_spans(note: str, parsed: Any) -> list[dict[str, Any]]:
    """Check each exact source quotation and reject overlapping or out-of-bounds spans."""
    if not isinstance(parsed, dict) or set(parsed) != {"entities"}:
        raise IntakeError("JSON thử lại sai cấu trúc.")
    entities = parsed["entities"]
    if not isinstance(entities, list):
        raise IntakeError("Danh sách thực thể thử lại sai cấu trúc.")
    spans = []
    for region in entities:
        if not isinstance(region, dict) or set(region) != {"label", "start", "value"}:
            raise IntakeError("Vùng thử lại phải có đúng label, start và value.")
        label, start, value = region["label"], region["start"], region["value"]
        if type(start) is not int or start < 0 or not isinstance(value, str) or not value.strip():
            raise IntakeError("Vị trí hoặc chuỗi thử lại không hợp lệ.")
        end = start + len(value)
        if label not in GOLD_LABELS or value.strip() != value or note[start:end] != value:
            raise IntakeError("Vùng thử lại không khớp nguyên văn tại vị trí đã khai báo.")
        spans.append({"label": label, "start": start, "end": end})
    try:
        checked = parse_note(
            {"note_id": "blind", "family_id": "blind", "text": note, "entities": spans}
        )
    except (TypeError, ValueError):
        raise IntakeError("Vùng thử lại chồng lấn hoặc có biên sai.") from None
    return [
        {"label": span.label, "start": span.start, "end": span.end} for span in checked.entities
    ]
