"""Read Arena lifecycle, Trackio curves and private-evaluation scores; never submit."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from huggingface_hub import get_token
import requests


ARENA = "https://openenvarena-arena.hf.space"
TRACKIO = "https://openenvarena-training.hf.space"


def read_json(url, *, token=None, payload=None):
    """Trackio POSTs here are read-only; credentials only go to Arena GETs."""
    try:
        if payload is None:
            headers = {"Authorization": "Bearer " + token} if token else {}
            response = requests.get(url, headers=headers, timeout=(10, 30))
        else:
            response = requests.post(url, json=payload, timeout=(10, 30))
        text = response.text.replace(token, "[REDACTED]") if token else response.text
        try:
            body = json.loads(text)
        except ValueError:
            return {"http_status": response.status_code, "error": "non-JSON response"}
        if not response.ok:
            return {"http_status": response.status_code, "error": body}
        return body
    except requests.RequestException as error:
        # Exception messages can include request details; retain only their type.
        return {"error": type(error).__name__}


def unwrap(value):
    if isinstance(value, dict) and not value.get("error") and "data" in value:
        value = value["data"]
        if isinstance(value, str):
            try:
                return json.loads(value)
            except ValueError:
                return {"error": "unrecognized Trackio data"}
    return value


def trackio(dashboard):
    query = parse_qs(urlparse(dashboard).query)
    if not query.get("project") or not query.get("runs"):
        return {"error": "dashboard has no project/run identity"}
    project, run = query["project"][0], query["runs"][0]
    identity = {"project": project, "run": run, "run_id": run}
    summary = unwrap(read_json(TRACKIO + "/api/get_run_summary", payload=identity))
    result = {"identity": identity, "dashboard": dashboard, "summary": summary}
    if not isinstance(summary, dict) or summary.get("error"):
        return result
    metrics = summary.get("metrics", [])
    if isinstance(metrics, dict):
        metrics = list(metrics)
    if not isinstance(metrics, list) or any(not isinstance(m, str) for m in metrics):
        result["error"] = "unrecognized metric inventory; inspect summary before querying"
        return result
    with ThreadPoolExecutor(max_workers=4) as pool:
        values = pool.map(lambda name: unwrap(read_json(
            TRACKIO + "/api/get_metric_values", payload={**identity, "metric_name": name}
        )), metrics)
        result["curves"] = dict(zip(metrics, values))
    result["logs"] = unwrap(read_json(TRACKIO + "/api/get_logs", payload=identity))
    return result


def collect():
    token = get_token()
    if not token:
        raise RuntimeError("HF CLI authentication unavailable; authenticate privately")
    listing = read_json(ARENA + "/api/openenv/submissions", token=token)
    if not isinstance(listing, dict) or not isinstance(listing.get("submissions"), list):
        return {"error": "Arena submissions unavailable", "response": listing}
    records = []
    for submission in listing["submissions"]:
        if not submission.get("submission_id", "").startswith("mimo-"):
            continue
        run = submission.get("run") or {}
        record = {"submission": submission}
        if run.get("run_id"):
            base = ARENA + "/api/openenv/runs/" + run["run_id"]
            with ThreadPoolExecutor(max_workers=3) as pool:
                status = pool.submit(read_json, base, token=token)
                events = pool.submit(read_json, base + "/events", token=token)
                metrics = pool.submit(trackio, run["dashboard"]) if run.get("dashboard") else None
                record.update(run=status.result(), events=events.result())
                record["trackio"] = metrics.result() if metrics else {"error": "dashboard unavailable"}
        records.append(record)
    leaderboard = read_json(ARENA + "/api/leaderboard")
    if isinstance(leaderboard, dict) and "entries" in leaderboard:
        leaderboard = {
            "benchmark": leaderboard.get("benchmark"),
            "baseline": leaderboard.get("baseline"),
            "entries": [x for x in leaderboard["entries"] if x.get("user") == "akseljoonas"],
            "runs": [x for x in leaderboard.get("runs", []) if x.get("user") == "akseljoonas"],
        }
    # Redact once more across public response bodies before persisting anything.
    return json.loads(json.dumps({
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "submissions": records, "leaderboard": leaderboard,
    }).replace(token, "[REDACTED]"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    snapshot = collect()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, indent=2) + "\n")
    if snapshot.get("error"):
        print(json.dumps(snapshot))
        raise SystemExit(1)
    for record in snapshot["submissions"]:
        submission, run = record["submission"], record.get("run", {})
        metrics = record.get("trackio", {}).get("summary", {})
        print(json.dumps({
            "submission_id": submission["submission_id"],
            "run_id": run.get("run_id"), "state": run.get("state"),
            "policy_version": run.get("policy_version"), "error": run.get("error"),
            "slot": submission.get("slot"), "dashboard": (submission.get("run") or {}).get("dashboard"),
            "trackio": {k: metrics.get(k) for k in ("error", "num_logs", "last_step", "metrics")}
                if isinstance(metrics, dict) else {"error": "unrecognized summary"},
            "evaluation": run.get("evaluation") or submission.get("evaluation"),
        }))


if __name__ == "__main__":
    main()
