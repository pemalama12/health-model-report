"""Standalone HTML reports with inline SVG and no external assets."""

from html import escape


def fmt(value, percent=False):
    return "N/A" if value is None else (f"{value:.1%}" if percent else f"{value:.3f}")


def ci(value, percent=False):
    return "interval unavailable" if value is None else f"{fmt(value[0], percent)}–{fmt(value[1], percent)}"


def chart(points, xkey, ykey, title):
    path = " ".join(f"{40 + p[xkey] * 300:.2f},{330 - p[ykey] * 290:.2f}" for p in points)
    dots = "".join(f'<circle cx="{40 + p[xkey] * 300:.2f}" cy="{330 - p[ykey] * 290:.2f}" r="4" fill="#16796b"/>' for p in points)
    whiskers = "".join(f'<path d="M{40+p[xkey]*300:.2f} {330-p["ci"][0]*290:.2f}V{330-p["ci"][1]*290:.2f}" stroke="#8ab9a9" stroke-width="2"/>' for p in points if "ci" in p)
    return f'''<svg viewBox="0 0 380 380" role="img" aria-label="{escape(title, quote=True)}">
    <path d="M40 40V330H340" fill="none" stroke="#b9c8c5"/><path d="M40 330L340 40" stroke="#b9c8c5" stroke-dasharray="5 6"/>
    <polyline points="{path}" fill="none" stroke="#16796b" stroke-width="3"/>{whiskers}{dots}
    <text x="28" y="350" font-size="12">0</text><text x="335" y="350" font-size="12">1</text><text x="20" y="45" font-size="12">1</text>
    </svg>'''


def render_report(result, title="Health Model Report"):
    m = result["overall"]
    cards = "".join(f'<div class="card"><small>{label}</small><strong>{fmt(m[key], pct)}</strong></div>'
                    for label, key, pct in [("AUROC", "auroc", False), ("Average precision", "average_precision", False),
                                            ("Recall / sensitivity", "recall", True), ("Precision", "precision", True),
                                            ("Specificity", "specificity", True), ("Brier score · lower is better", "brier", False)])
    subgroup_rows = "".join(f'<tr><td>{escape(s["label"])}</td><td>{s["n"]}</td><td>{s["positives"]}</td><td>{fmt(s["auroc"])}<small>{ci(s["auroc_ci"])}</small></td><td>{fmt(s["recall"], True)}<small>{ci(s["recall_ci"], True)}</small></td><td>{fmt(s["precision"], True)}</td><td>{fmt(s["brier"])}</td></tr>' for s in result["subgroups"])
    notices = "".join(f"<p>{escape(w)}</p>" for w in result["warnings"])
    auc_ci = m["auroc_ci"]
    ci_text = "Unavailable" if auc_ci is None else f"{auc_ci[0]:.3f}–{auc_ci[1]:.3f}"
    recall_ci = m["recall_ci"]
    recall_text = "Unavailable" if recall_ci is None else f"{recall_ci[0]:.1%}–{recall_ci[1]:.1%}"
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{escape(title)}</title><style>
    *{{box-sizing:border-box}}body{{font:16px/1.6 system-ui,sans-serif;color:#243c38;background:#f5f7f4;margin:0;padding:40px}}main{{max-width:1100px;margin:auto}}h1{{font-size:40px;letter-spacing:-1.5px}}h2{{font-size:22px}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}.card,section{{background:white;border:1px solid #dce4e0;border-radius:16px;padding:24px;margin-bottom:16px}}small{{display:block;color:#647a74}}strong{{display:block;font-size:32px}}.charts{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}svg{{width:100%;max-height:330px}}table{{border-collapse:collapse;width:100%}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #e4e9e5}}.muted{{color:#647a74}}.table{{overflow:auto}}@media(max-width:650px){{body{{padding:18px}}.grid,.charts{{grid-template-columns:1fr}}}}@media print{{body{{background:white;padding:0}}section{{break-inside:avoid}}}}
    </style><main><p class="muted">HEALTH MODEL REPORT / EVALUATION SNAPSHOT</p><h1>{escape(title)}</h1>
    <p>{m["n"]:,} patients · {m["positives"]:,} positive outcomes · prevalence {m["prevalence"]:.1%} · threshold {result["threshold"]:.2f}</p>
    <div class="grid">{cards}</div><p>AUROC 95% bootstrap interval: {ci_text}. Recall 95% Wilson interval: {recall_text}.</p>
    <div class="charts"><section><h2>Calibration</h2><p class="muted">X: mean predicted probability · Y: observed outcome rate</p>{chart(result["calibration"], "predicted", "observed", "Calibration plot")}</section>
    <section><h2>ROC curve</h2><p class="muted">X: false positive rate · Y: true positive rate</p>{chart(result["roc"], "x", "y", "ROC curve") if result["roc"] else '<p>Unavailable: requires both outcome classes.</p>'}</section></div>
    <section><h2>Confusion matrix</h2><p>True positives: {m["tp"]} · False positives: {m["fp"]} · True negatives: {m["tn"]} · False negatives: {m["fn"]}</p></section>
    <section><h2>Subgroups{": " + escape(result["group"]) if result["group"] else ""}</h2><div class="table"><table><thead><tr><th>Group</th><th>Patients</th><th>Positive</th><th>AUROC</th><th>Recall</th><th>Precision</th><th>Brier</th></tr></thead><tbody>{subgroup_rows or '<tr><td colspan="7">No subgroup column selected.</td></tr>'}</tbody></table></div>{notices}</section>
    <section><h2>Methods and interpretation</h2><p>{escape(result["methods"])}</p><p>This report evaluates supplied predictions. It does not validate clinical use, establish causal bias, or verify the source dataset. Use independent held-out patients; repeated encounters require a different uncertainty method.</p><p>Raw patient records are not embedded in this export. Aggregate subgroup labels may still be sensitive; review before sharing.</p></section></main></html>'''
