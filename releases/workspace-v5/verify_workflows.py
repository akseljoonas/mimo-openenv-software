"""Deterministic real Docker/OpenEnv correctness checks, with no model calls."""
import argparse
from datetime import datetime, timezone
import hashlib
import inspect
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time
import uuid

import requests
from websockets.sync.client import connect
from vendor import tasks

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("image")
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
cases = json.loads((ROOT / "cases.json").read_text())
report = {"image": args.image, "observed_at": datetime.now(timezone.utc).isoformat(),
          "kind": "deterministic correctness, not a model evaluation", "checks": [], "cases": []}
name = "workflow-check-" + uuid.uuid4().hex[:10]


def check(label, condition):
    if not condition:
        raise AssertionError(label)
    report["checks"].append(label)


def reference_script(family):
    # Only the independent file solver is sent through the action. Generator,
    # expected outputs and grader are excluded. This script never enters images.
    return (
        "import json, itertools, math, heapq\nfrom fractions import Fraction\n"
        "from collections import deque\nfrom pathlib import Path\nfrom typing import Any\n"
        + inspect.getsource(tasks._load) + "\n" + inspect.getsource(tasks.oracle_answer)
        + "\ntask={'task_id':" + repr(family)
        + ",'files':{p.name:p.read_text() for p in Path('.').glob('*.json')}}\n"
        "Path('answer.json').write_text(json.dumps(oracle_answer(task)))\n"
    )


try:
    subprocess.run(["docker", "run", "--rm", "-d", "--platform", "linux/amd64", "--name", name,
                    "--cpus", "2", "--memory", "16g", "-p", "127.0.0.1::8000", args.image],
                   check=True, capture_output=True, text=True)
    url = "http://" + subprocess.check_output(["docker", "port", name, "8000"], text=True).strip()
    start = time.monotonic()
    while time.monotonic() - start < 120:
        try:
            if requests.get(url + "/health", timeout=2).ok:
                break
        except requests.RequestException:
            pass
        time.sleep(1)
    else:
        raise RuntimeError("health deadline exceeded")
    report["ready_seconds"] = round(time.monotonic() - start, 3)
    check("health_within_120_seconds", True)
    schema = requests.get(url + "/schema", timeout=10).json()
    expected_schema = json.loads((ROOT.parent / "signal-v4/submission.json").read_text())["schema"]
    check("schema_identical_to_original_mimo_images", all(schema[k] == v for k, v in expected_schema.items()))
    report["schema"] = schema
    validation = subprocess.run([str(Path(sys.executable).with_name("openenv")), "validate", "--url", url],
                                capture_output=True, text=True)
    report["openenv_validation"] = validation.stdout + validation.stderr
    check("openenv_validate", validation.returncode == 0)
    with connect(url.replace("http:", "ws:") + "/ws", open_timeout=30) as ws:
        def call(kind, data):
            ws.send(json.dumps({"type": kind, "data": data}))
            response = json.loads(ws.recv(timeout=90))
            if response["type"] != "observation":
                raise AssertionError(response)
            return response["data"]

        def reset(case_id, seed=1):
            return call("reset", {"task_id": case_id, "seed": seed})

        def shell(command):
            result = call("step", {"operation": "shell", "command": command})
            if result["observation"]["exit_code"] != 0:
                report["failed_shell"] = result
            check("shell_action_succeeded", result["observation"]["exit_code"] == 0)
            return result

        def finish():
            result = call("step", {"operation": "finish"})
            check("terminal_valid_reward", result["done"] and 0 <= result["reward"] <= 1)
            return result

        def write_answer(answer):
            shell("printf %s " + shlex.quote(json.dumps(answer)) + " > answer.json")

        for case_id, case in cases.items():
            began = time.monotonic()
            task = tasks.make_task(case["family"], case["seed"], case["difficulty"])
            check("reset_identity_" + case_id, reset(case_id)["observation"]["task_id"] == case_id)
            check("unsolved_zero_" + case_id, finish()["reward"] == 0)
            reset(case_id)
            script = reference_script(case["family"])
            check("reference_fits_action_budget", len(script) + 50 < 16000)
            action = shell("python3 - <<'WORKFLOW_REFERENCE'\n" + script + "\nWORKFLOW_REFERENCE")
            positive = finish()
            check("file_derived_reference_one_" + case_id, positive["reward"] == 1)
            check("terminal_stable", call("step", {"operation": "finish"}) == positive)
            reset(case_id, 99999)
            shell("test ! -e answer.json")
            actual = json.loads(shell("python3 - <<'READ_INPUTS'\nimport json\nfrom pathlib import Path\nprint(json.dumps({p.name:p.read_text() for p in Path('.').glob('*.json')}))\nREAD_INPUTS")["observation"]["output"])
            check("fixed_identity_across_seeds_" + case_id, actual == task["files"])
            partial = next({k: v} for k, v in task["expected"].items() if tasks.grade(task, {k: v}) > 0)
            write_answer(partial)
            partial_reward = finish()["reward"]
            check("exact_original_partial_reward_" + case_id, partial_reward == tasks.grade(task, partial) and 0 < partial_reward < 1)
            reset(case_id)
            write_answer({**task["expected"], "unexpected_key": "reject"})
            check("extra_key_rejected_" + case_id, finish()["reward"] == 0)
            report["cases"].append({"task_id": case_id, "source_files_sha256": hashlib.sha256(json.dumps(actual, sort_keys=True).encode()).hexdigest(),
                                    "reference_reward": 1, "unsolved_reward": 0, "partial_reward": partial_reward,
                                    "wall_seconds": round(time.monotonic() - began, 3)})

        first = next(iter(cases))
        reset(first)
        shell("test $(id -u) = 2000 && test ! -r /opt/arena/vendor/tasks.py && test ! -w /opt/arena/workflow_server.py && test ! -r /proc/1/mem && test ! -w /workspace")
        check("agent_cannot_read_or_modify_grader", True)
        for label, command in {
            "invalid_json": "printf '{' > answer.json",
            "deep_json": "python3 -c \"from pathlib import Path; Path('answer.json').write_text('['*2000+']'*2000)\"",
            "oversized": "truncate -s 20000 answer.json",
            "directory": "mkdir answer.json",
            "symlink_to_protected_source": "ln -s /opt/arena/vendor/tasks.py answer.json",
            "fifo": "mkfifo answer.json",
            "nonfinite": "printf '{\"affected\":NaN}' > answer.json",
            "non_utf8": "python3 -c \"from pathlib import Path; Path('answer.json').write_bytes(b'\\xff')\"",
            "source_tamper": "printf '{}' > modules.json; printf '{}' > answer.json",
        }.items():
            reset(first)
            shell(command)
            check(label + "_zero", finish()["reward"] == 0)
        reset(first)
        for _ in range(15):
            shell("true")
        last = call("step", {"operation": "shell", "command": "python3 - <<'WORKFLOW_REFERENCE'\n" + reference_script(cases[first]["family"]) + "\nWORKFLOW_REFERENCE"})
        check("last_action_executes_before_budget_grading", last["done"] and last["reward"] == 1)
        ws.send(json.dumps({"type": "reset", "data": {"task_id": "does-not-exist"}}))
        check("unknown_case_rejected", json.loads(ws.recv(timeout=10))["type"] == "error")
        reset(first)
        check("valid_reset_recovers_after_invalid_case", finish()["reward"] == 0)
    report["passed"] = True
finally:
    report["container_logs"] = subprocess.run(["docker", "logs", name], capture_output=True, text=True).stderr[-5000:]
    subprocess.run(["docker", "stop", name], capture_output=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"passed": report["passed"], "cases": len(report["cases"]), "checks": len(report["checks"])}))
