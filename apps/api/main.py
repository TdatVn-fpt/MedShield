# apps/api/main.py — Minimal G0 FastAPI application for environment smoke testing.
from fastapi import FastAPI

app = FastAPI(title="MedShield", version="0.1.0")


@app.get("/health")
def health() -> dict[str, object]:
    """health returns API readiness; the detection engine is not implemented in G0."""
    return {
        "status": "ok",
        "engines": [
            {"name": "medshield-rules", "status": "unavailable", "mode": "rules", "language": "vi"}
        ],
    }
