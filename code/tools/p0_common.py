"""Shared helpers for Phase-0 analysis scripts (not part of the prediction pipeline)."""
from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in [HERE, *HERE.parents] if (p / "dataset").is_dir())
DS = ROOT / "dataset"

RES_RE = re.compile(
    r"\b(?:account|search|support|analytics|cache|export|data_flow|backup|legal_hold|"
    r"tombstone|audit_record|email_delivery|object|marketing)_\d+\b"
)


def ts(s: str) -> datetime:
    return datetime.fromisoformat(s.strip().replace("Z", "+00:00"))


def read_csv(name: str) -> list[dict]:
    with (DS / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_text() -> dict[str, str]:
    """file_id -> text (PNG -> '')."""
    from pypdf import PdfReader

    out = {}
    for m in read_csv("evidence_files.csv"):
        p = DS / m["file_path"]
        if p.suffix == ".png":
            out[m["file_id"]] = ""
        elif p.suffix == ".pdf":
            out[m["file_id"]] = "\n".join(pg.extract_text() or "" for pg in PdfReader(p).pages)
        else:
            out[m["file_id"]] = p.read_text(encoding="utf-8")
    return out


def gold() -> dict[str, tuple[str, list[dict]]]:
    return {g["case_id"]: (g["deletion_status"], json.loads(g["steps_json"]))
            for g in read_csv("sample_output.csv")}
