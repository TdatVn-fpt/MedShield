# apps/api/schemas.py — Define the single validated HTTP entity and request contract.
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

Label = Literal["NAME", "DOB", "PHONE", "ID", "ADDR"]
Mode = Literal["rules", "ner", "hybrid"]
Language = Literal["vi", "en"]
LABELS: tuple[Label, ...] = ("NAME", "DOB", "PHONE", "ID", "ADDR")
MAX_ENTITIES = 2_000


class StrictModel(BaseModel):
    """StrictModel rejects extra fields so exports and requests have a stable contract."""

    model_config = ConfigDict(extra="forbid")


class Entity(StrictModel):
    """Entity describes a half-open Unicode codepoint span without copying its text."""

    start: StrictInt
    end: StrictInt
    label: Label
    source: str = Field(min_length=1, max_length=100)
    score: float = Field(ge=0, le=1, allow_inf_nan=False, strict=True)


EntityList = Annotated[list[Entity], Field(max_length=MAX_ENTITIES)]


class TextRequest(StrictModel):
    """TextRequest validates nonempty original text without Unicode normalization."""

    text: str = Field(min_length=1, max_length=50_000, strict=True)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        """validate_text rejects whitespace-only text and preserves all original codepoints."""
        if not value.strip():
            raise ValueError("empty text")
        return value


class AnalyzeRequest(TextRequest):
    """AnalyzeRequest selects an explicit language and engine configuration."""

    language: Language
    mode: Mode


class RedactRequest(TextRequest):
    """RedactRequest carries the reviewed spans; an empty list intentionally keeps text."""

    entities: EntityList


class Engine(StrictModel):
    """Engine identifies what actually ran or what is unavailable."""

    name: str
    status: Literal["available", "unavailable"]
    mode: Mode
    language: Language
    version: str | None = None
    model_revision: str | None = None


class Metadata(StrictModel):
    """Metadata counts selected occurrences, never original values or token maps."""

    entity_count: int
    counts_by_label: dict[Label, int]
    offset_unit: Literal["unicode_code_point"] = "unicode_code_point"


class RedactResponse(StrictModel):
    """RedactResponse contains only the redacted document and minimal metadata."""

    redacted_text: str
    metadata: Metadata


class AnalyzeResponse(StrictModel):
    """AnalyzeResponse exposes machine spans and preview before manual correction."""

    entities: EntityList
    redacted_text: str
    engine: Engine
