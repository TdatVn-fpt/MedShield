# scripts/check_source.py — Enforce source headers and the 299 physical line limit.
from pathlib import Path

EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".css"}
EXCLUDED = {
    ".git",
    ".venv",
    ".cache",
    ".specify",
    ".codex",
    "node_modules",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}


def check_sources() -> int:
    """check_sources prints violations and returns a shell exit code for handwritten sources."""
    violations = 0
    for path in sorted(Path(".").rglob("*")):
        if path.suffix not in EXTENSIONS or any(part in EXCLUDED for part in path.parts):
            continue
        if any(part.startswith(".venv-") for part in path.parts):
            continue
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        if len(lines) > 299:
            print(f"ERROR {path.as_posix()}: {len(lines)} lines (maximum 299)")
            violations += 1
        header_index = 1 if lines and lines[0].startswith("#!") else 0
        if len(lines) <= header_index or path.as_posix() not in lines[header_index]:
            print(f"ERROR {path.as_posix()}: missing relative-path purpose header")
            violations += 1
    print(f"Source policy: {violations} violation(s)")
    return int(violations > 0)


if __name__ == "__main__":
    raise SystemExit(check_sources())
