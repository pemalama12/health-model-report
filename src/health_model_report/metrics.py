"""Binary metrics; undefined values remain null rather than becoming zero."""

import math
from functools import lru_cache

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score, roc_curve

from .data import Dataset


def ratio(numerator, denominator):
    return float(numerator / denominator) if denominator else None


def wilson(successes, total):
    """95% Wilson score interval for a binomial proportion."""
    if not total:
        return None
    z = 1.959963984540054
    p = successes / total
    den = 1 + z * z / total
    center = (p + z * z / (2 * total)) / den
    width = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / den
    return [max(0, center - width), min(1, center + width)]


@lru_cache(maxsize=64)
def auc_interval(truth: tuple, scores: tuple):
    """Seeded 200-resample percentile bootstrap, assuming independent patients."""
    y, p = np.asarray(truth), np.asarray(scores)
    if len(set(truth)) < 2:
        return None
    rng = np.random.default_rng(42)
    estimates = []
    for _ in range(200):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(y[idx])) == 2:
            estimates.append(roc_auc_score(y[idx], p[idx]))
    return [float(x) for x in np.quantile(estimates, [0.025, 0.975])] if len(estimates) >= 100 else None


def summarize(rows, threshold):
    truth = np.array([r["y_true"] for r in rows])
    scores = np.array([r["y_score"] for r in rows])
    pred = scores >= threshold
    tp = int(np.sum(pred & (truth == 1)))
    fp = int(np.sum(pred & (truth == 0)))
    tn = int(np.sum(~pred & (truth == 0)))
    fn = int(np.sum(~pred & (truth == 1)))
    both = len(np.unique(truth)) == 2
    return {
        "n": len(rows), "positives": int(sum(truth)), "prevalence": float(np.mean(truth)),
        "auroc": float(roc_auc_score(truth, scores)) if both else None,
        "auroc_ci": auc_interval(tuple(truth.tolist()), tuple(scores.tolist())) if both else None,
        "average_precision": float(average_precision_score(truth, scores)) if sum(truth) else None,
        "brier": float(brier_score_loss(truth, scores)),
        "accuracy": ratio(tp + tn, len(rows)), "precision": ratio(tp, tp + fp),
        "recall": ratio(tp, tp + fn), "specificity": ratio(tn, tn + fp),
        "recall_ci": wilson(tp, tp + fn), "precision_ci": wilson(tp, tp + fp),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
    }


def evaluate(dataset: Dataset, threshold: float = 0.5, group: str | None = None):
    if not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("Threshold must be a finite number between 0 and 1.")
    if group and group not in dataset.groups:
        raise ValueError("Choose a subgroup column present in the CSV.")
    rows = dataset.rows
    overall = summarize(rows, threshold)
    y = np.array([r["y_true"] for r in rows])
    p = np.array([r["y_score"] for r in rows])
    calibration = []
    bin_ids = np.minimum((p * 10).astype(int), 9)
    for bin_id in range(10):
        mask = bin_ids == bin_id
        if mask.any():
            positives, total = int(sum(y[mask])), int(sum(mask))
            calibration.append({"predicted": float(np.mean(p[mask])), "observed": positives / total,
                                "n": total, "ci": wilson(positives, total)})
    curve = []
    if len(np.unique(y)) == 2:
        fpr, tpr, _ = roc_curve(y, p)
        curve = [{"x": float(x), "y": float(v)} for x, v in zip(fpr, tpr)]
    subgroups = []
    if group:
        for value in sorted({r[group] for r in rows}):
            summary = summarize([r for r in rows if r[group] == value], threshold)
            subgroups.append({"label": value, **summary})
    warnings = []
    if overall["auroc"] is None:
        warnings.append("Only one outcome class is present. AUROC and ROC curve are undefined.")
    if overall["precision"] is None:
        warnings.append("No patients are predicted positive at this threshold; precision is undefined.")
    if any(s["n"] < 30 or s["positives"] < 10 or s["n"] - s["positives"] < 10 for s in subgroups):
        warnings.append("Some subgroups have fewer than 30 patients or fewer than 10 positive/negative outcomes. Estimates may be unstable.")
    return {"threshold": threshold, "group": group, "available_groups": list(dataset.groups),
            "overall": overall, "subgroups": subgroups, "calibration": calibration,
            "roc": curve, "warnings": warnings,
            "methods": "Positive prediction: score ≥ threshold. AUROC intervals: 200 patient bootstrap resamples, percentile 95%, seed 42. Recall/precision and calibration intervals: Wilson 95%. Assumes independent, held-out patients. Average precision uses the non-interpolated sklearn definition. Calibration uses ten equal-width bins; empty bins are omitted. Subgroup differences describe performance and do not establish fairness or clinical suitability."}
