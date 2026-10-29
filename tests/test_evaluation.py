import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

import pytest

from health_model_report.app import Handler
from health_model_report.data import demo_csv, parse_csv
from health_model_report.metrics import evaluate, wilson
from health_model_report.report import render_report


def test_known_ranking_calibration_and_threshold_counts():
    # Classic four-patient ranking example: AUROC = 3/4, AP = 5/6.
    data = parse_csv("y_true,y_score,group\n0,0.1,A\n0,0.4,A\n1,0.35,B\n1,0.8,B\n")
    report = evaluate(data, 0.4, "group")
    m = report["overall"]
    assert m["auroc"] == pytest.approx(0.75)
    assert m["average_precision"] == pytest.approx(5 / 6)
    assert m["brier"] == pytest.approx(0.158125)
    assert [m[k] for k in ("tp", "fp", "tn", "fn")] == [1, 1, 1, 1]
    assert m["precision"] == m["recall"] == m["specificity"] == 0.5
    assert report["subgroups"][0]["auroc"] is None
    assert report["subgroups"][1]["specificity"] is None
    assert report["warnings"]


@pytest.mark.parametrize("truth", [0, 1])
def test_single_class_and_no_alerts_are_explicit(truth):
    report = evaluate(parse_csv(f"y_true,y_score\n{truth},0.1\n{truth},0.2\n"), 0.9)
    assert report["overall"]["auroc"] is None
    assert report["overall"]["precision"] is None
    assert report["roc"] == []
    assert report["warnings"]
    json.dumps(report, allow_nan=False)


def test_bins_partition_boundary_scores_once():
    scores = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
    data = parse_csv("y_true,y_score\n" + "\n".join(f"{i % 2},{p}" for i, p in enumerate(scores)))
    result = evaluate(data)
    assert sum(b["n"] for b in result["calibration"]) == len(scores)
    assert len(result["calibration"]) == 10
    assert result["calibration"][-1]["n"] == 2


def test_wilson_matches_reference_and_handles_undefined():
    assert wilson(5, 10) == pytest.approx([0.236593, 0.763407], abs=1e-6)
    assert wilson(0, 0) is None


@pytest.mark.parametrize("text,match", [
    ("a,b\n1,0\n", "must include"),
    ("y_true,y_score\n1,nan\n0,.2\n", "finite"),
    ("y_true,y_score\n2,.5\n0,.2\n", "0/1"),
    ("y_true,y_score\n1,1.1\n0,.2\n", "between"),
    ("y_true,y_score\n1,.5\n", "at least two"),
    ("y_true,y_score,y_score\n1,.2,.2\n0,.1,.1\n", "unique"),
    ("y_true,y_score\n1,.2,extra\n0,.1\n", "column count"),
    ("patient_id,y_true,y_score\nx,1,.2\nx,0,.1\n", "unique"),
    ("y_true,y_score\n1,\n0,.1\n", "numeric"),
])
def test_bad_inputs_are_rejected(text, match):
    with pytest.raises(ValueError, match=match):
        parse_csv(text)


def test_continuous_group_is_rejected_and_missing_labels_explicit():
    with pytest.raises(ValueError, match="Bin continuous"):
        parse_csv("y_true,y_score,age\n" + "\n".join(f"{i%2},.5,{i}" for i in range(31)))
    data = parse_csv("y_true,y_score,group\n1,.8,\n0,.2,A\n")
    assert data.rows[0]["group"] == "(missing)"


@pytest.mark.parametrize("threshold", [float("nan"), float("inf"), -0.1, 1.1])
def test_threshold_validation(threshold):
    with pytest.raises(ValueError, match="Threshold"):
        evaluate(parse_csv("y_true,y_score\n1,.8\n0,.2\n"), threshold)


def test_report_escapes_user_content_and_excludes_raw_records():
    data = parse_csv('patient_id,y_true,y_score,group\nprivate-id,1,.8,<script>alert(1)</script>\nanother-id,0,.2,A\n')
    html = render_report(evaluate(data, group="group"), title="<test>")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "private-id" not in html
    assert "https://" not in html
    assert "<svg" in html


def test_demo_is_deterministic_and_exposes_intended_difference():
    assert demo_csv(10) == demo_csv(10)
    data = parse_csv(demo_csv())
    result = evaluate(data, group="age_group")
    groups = {s["label"]: s for s in result["subgroups"]}
    assert groups["65+"]["recall"] < groups["40–64"]["recall"]
    assert result["overall"]["auroc_ci"] == evaluate(data)["overall"]["auroc_ci"]


def test_http_import_export_and_cross_origin_rejection():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    client = HTTPConnection("127.0.0.1", server.server_port)
    try:
        client.request("GET", "/")
        response = client.getresponse()
        assert response.status == 200
        assert b"Understand your predictions" in response.read()
        payload = json.dumps({"csv": "y_true,y_score\n1,.8\n0,.2\n", "threshold": 0.3})
        client.request("POST", "/api/evaluate", payload, {"Content-Type": "application/json"})
        response = client.getresponse()
        assert response.status == 200
        assert json.loads(response.read())["overall"]["tp"] == 1
        client.request("POST", "/api/report", payload, {"Content-Type": "application/json"})
        response = client.getresponse()
        assert response.status == 200
        assert "attachment" in response.getheader("Content-Disposition")
        assert b"Confusion matrix" in response.read()
        client.request("POST", "/api/export", payload, {"Content-Type": "application/json"})
        response = client.getresponse()
        assert response.status == 200
        url = json.loads(response.read())["url"]
        client.request("GET", url + "?download=1")
        response = client.getresponse()
        assert response.status == 200
        assert "attachment" in response.getheader("Content-Disposition")
        assert b"Confusion matrix" in response.read()
        client.request("POST", "/api/evaluate", payload, {"Origin": "https://example.com"})
        response = client.getresponse()
        assert response.status == 403
        response.read()
        client.request("POST", "/api/evaluate", "{", {"Content-Type": "application/json"})
        response = client.getresponse()
        assert response.status == 400
        response.read()
    finally:
        client.close()
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
