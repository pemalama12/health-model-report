"""Strict CSV validation and a reproducible, entirely synthetic example."""

import csv
import io
import math
import random
from collections import Counter
from dataclasses import dataclass

MAX_ROWS = 50_000
MAX_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class Dataset:
    rows: tuple[dict, ...]
    groups: tuple[str, ...]


def parse_csv(text: str) -> Dataset:
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise ValueError("CSV is too large. Maximum size is 8 MB.")
    try:
        reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")), strict=True)
        fields = reader.fieldnames or []
        if any(not f.strip() or len(f) > 120 for f in fields):
            raise ValueError("Column names must be nonempty and at most 120 characters long.")
        if len(fields) != len(set(fields)):
            raise ValueError("Column names must be unique.")
        if not {"y_true", "y_score"}.issubset(fields):
            raise ValueError("CSV must include y_true (0 or 1) and y_score (probability from 0 to 1).")
        groups = tuple(f for f in fields if f not in {"y_true", "y_score", "patient_id"})
        if len(groups) > 12:
            raise ValueError("Include at most 12 subgroup columns.")
        rows = []
        ids = set()
        for line, raw in enumerate(reader, 2):
            if len(rows) >= MAX_ROWS:
                raise ValueError(f"Maximum supported dataset size is {MAX_ROWS:,} rows.")
            if None in raw or any(v is None for v in raw.values()):
                raise ValueError(f"Row {line}: column count does not match the header.")
            try:
                truth, score = float(raw["y_true"]), float(raw["y_score"])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Row {line}: y_true and y_score must be numeric.") from exc
            if truth not in (0, 1) or not math.isfinite(score) or not 0 <= score <= 1:
                raise ValueError(f"Row {line}: use y_true 0/1 and a finite y_score between 0 and 1.")
            if "patient_id" in fields:
                patient_id = raw["patient_id"].strip()
                if not patient_id or patient_id in ids:
                    raise ValueError(f"Row {line}: patient_id must be nonempty and unique; use one row per patient.")
                ids.add(patient_id)
            row = {"y_true": int(truth), "y_score": score}
            for group in groups:
                value = raw[group].strip() or "(missing)"
                if len(value) > 120:
                    raise ValueError(f"Row {line}: subgroup labels must be 120 characters or shorter.")
                row[group] = value
            rows.append(row)
    except csv.Error as exc:
        raise ValueError(f"Invalid CSV: {exc}") from exc
    if len(rows) < 2:
        raise ValueError("Include at least two patients.")
    for group in groups:
        if len(Counter(r[group] for r in rows)) > 30:
            raise ValueError(f"Column {group!r} has more than 30 values. Bin continuous values (for example, age bands) or remove identifier columns.")
    return Dataset(tuple(rows), groups)


def demo_csv(n: int = 1200, seed: int = 42) -> str:
    """Invented readmission scenario with intentionally underpredicted older adults."""
    rng = random.Random(seed)
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["patient_id", "y_true", "y_score", "age_group", "care_site"])
    for i in range(n):
        age = rng.choices(["18–39", "40–64", "65+"], weights=[25, 40, 35])[0]
        site = rng.choice(["North", "Central", "South"])
        latent = rng.gauss(-1.2, 1.35) + (0.7 if age == "65+" else 0)
        risk = 1 / (1 + math.exp(-latent))
        truth = int(rng.random() < risk)
        prediction = latent + rng.gauss(0, 0.45) - (1.0 if age == "65+" else 0)
        score = 1 / (1 + math.exp(-prediction))
        writer.writerow([f"SYN-{i + 1:05d}", truth, f"{score:.6f}", age, site])
    return output.getvalue()
