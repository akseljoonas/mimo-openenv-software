"""Create the fixed 34-task request after its new public image is digest-pinned."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

from vendor.tasks import make_task

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--image", required=True)
parser.add_argument("--source-revision", required=True)
args = parser.parse_args()
assert re.fullmatch(r"ghcr.io/akseljoonas/mimo-openenv-software@sha256:[a-f0-9]{64}", args.image)
assert re.fullmatch(r"[a-f0-9]{40}", args.source_revision)
previous = ROOT.parent / "signal-v4"
old_request = json.loads((previous / "submission.json").read_text())
old_rows = {row["task_id"]: row for row in map(json.loads, (previous / "tasks.jsonl").read_text().splitlines())}
cases = json.loads((ROOT / "cases.json").read_text())
rows, request_tasks = [], []
retained = iter(["format-code-task-000666", "format-code-task-001926"])
(ROOT / "tasks").mkdir(exist_ok=True)
for index, (case_id, case) in enumerate(cases.items(), 1):
    task = make_task(case["family"], case["seed"], case["difficulty"])
    rows.append({"task_id": case_id, "dataset_type": "public-data-workflow", "image": args.image,
                 "family": case["family"], "seed": case["seed"], "difficulty": case["difficulty"],
                 "prompt": task["prompt"], "files_json": json.dumps(task["files"], sort_keys=True),
                 "source_revision": "4657e5b82e124917b01d79ee5e9de41badb48fda"})
    request_tasks.append({"task_id": case_id, "image": args.image, "split": "train",
                          "reset_wall_s": 120, "rollout_wall_s": 300, "verifier_wall_s": 30,
                          "tool_wall_s": 60, "tool_calls_total": 16, "tool_calls_per_minute": 60,
                          "completion_tokens": 8192, "context_tokens": 16384,
                          "memory_gib": 16, "cpu_floor_vcpus": 2, "workspace_gib": 10})
    if index in (8, 24):
        task_id = next(retained)
        row = dict(old_rows[task_id])
        raw = (previous / "tasks" / (task_id + ".json")).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row["instance_json_sha256"]
        rows.append(row)
        request_tasks.append(next(dict(t) for t in old_request["tasks"] if t["task_id"] == task_id))
        shutil.copyfile(previous / "tasks" / (task_id + ".json"), ROOT / "tasks" / (task_id + ".json"))
request = {"submission_id": "mimo-workspace-v5-20261012",
           "name": "Fixed workspace reasoning and original MiMo repairs (34 tasks)",
           "image": args.image, "schema": old_request["schema"], "tasks": request_tasks,
           "example_actions": [{"operation": "finish"}], "finish_action": {"operation": "finish"},
           "dataset": "akseljoonas/mimo-openenv-workspace-v5",
           "source": "https://github.com/akseljoonas/mimo-openenv-software/tree/" + args.source_revision + "/releases/workspace-v5"}
(ROOT / "tasks.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
(ROOT / "submission.json").write_text(json.dumps(request, indent=2) + "\n")
print(json.dumps({"tasks": len(rows), "images": len({t['image'] for t in request_tasks}), "submission_id": request['submission_id']}))
