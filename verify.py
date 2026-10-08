"""Replay real Docker/WebSocket episodes; reference repairs never enter images."""
import argparse
import json
from pathlib import Path
import subprocess
import shlex
import time
import uuid

import requests
from websockets.sync.client import connect


parser = argparse.ArgumentParser()
parser.add_argument("image")
parser.add_argument("task_id")
parser.add_argument("--solution", type=Path)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
name = "mimo-check-" + uuid.uuid4().hex[:10]
report = {"image": args.image, "task_id": args.task_id, "checks": []}


def check(label, condition):
    assert condition, label
    report["checks"].append(label)


try:
    subprocess.run([
        "docker", "run", "--rm", "-d", "--platform", "linux/amd64",
        "--name", name, "--cpus", "2", "--memory", "16g",
        "-p", "127.0.0.1::8000", args.image,
    ], check=True, capture_output=True, text=True)
    binding = subprocess.check_output(["docker", "port", name, "8000"], text=True).strip()
    url = "http://" + binding
    start = time.monotonic()
    while time.monotonic() - start < 120:
        try:
            if requests.get(url + "/health", timeout=2).status_code == 200:
                break
        except requests.RequestException:
            pass
        time.sleep(1)
    else:
        raise RuntimeError("health deadline exceeded")
    report["ready_seconds"] = round(time.monotonic() - start, 2)
    check("health_within_120_seconds", True)
    report["schema"] = requests.get(url + "/schema", timeout=10).json()
    result = subprocess.run(["openenv", "validate", "--url", url], capture_output=True, text=True)
    report["openenv_validation"] = result.stdout + result.stderr
    check("openenv_endpoint_validation", result.returncode == 0)
    with connect(url.replace("http:", "ws:") + "/ws", open_timeout=30) as ws:
        def call(kind, data):
            ws.send(json.dumps({"type": kind, "data": data}))
            response = json.loads(ws.recv(timeout=1850))
            assert response["type"] == "observation", response
            return response["data"]

        def shell(command):
            return call("step", {"operation": "shell", "command": command})

        reset = call("reset", {"task_id": args.task_id})
        check("reset_task_identity", reset["observation"]["task_id"] == args.task_id and not reset["done"])
        protected = shell("test $(id -u) = 2000 && test ! -r /opt/arena/instance.json && test ! -w /opt/arena/server.py")
        check("unprivileged_agent_and_protected_verifier", protected["observation"]["exit_code"] == 0)
        history = shell("git rev-list --all --not HEAD")
        check("no_future_git_history", history["observation"]["exit_code"] == 0 and not history["observation"]["output"].strip())
        negative = call("step", {"operation": "finish"})
        report["unsolved_result"] = negative
        check("unsolved_terminal_reward_zero", negative["done"] and negative["reward"] == 0)
        repeated = call("step", {"operation": "finish"})
        check("terminal_reward_is_stable", repeated == negative)
        call("reset", {"task_id": args.task_id})
        shell("printf changed > .arena-reset-marker")
        call("reset", {"task_id": args.task_id})
        check("reset_removes_previous_edits", shell("test ! -e .arena-reset-marker")["observation"]["exit_code"] == 0)
        probe = "sh -c 'id -u > /tmp/arena-git-hook-uid'"
        shell("git config core.fsmonitor " + shlex.quote(probe))
        call("step", {"operation": "finish"})
        hook_uid = subprocess.check_output(["docker", "exec", name, "cat", "/tmp/arena-git-hook-uid"], text=True).strip()
        check("verifier_git_hooks_are_unprivileged", hook_uid == "2000")
        call("reset", {"task_id": args.task_id})
        if args.solution:
            script = args.solution.read_text()
            repaired = shell("python - <<'ARENA_REPAIR'\n" + script + "\nARENA_REPAIR")
            check("reference_repair_applied_through_action", repaired["observation"]["exit_code"] == 0)
            positive = call("step", {"operation": "finish"})
            report["reference_result"] = positive
            check("reference_terminal_reward_one", positive["done"] and positive["reward"] == 1)
            call("reset", {"task_id": args.task_id})
            reset_again = call("step", {"operation": "finish"})
            check("reset_restores_unsolved_task", reset_again["done"] and reset_again["reward"] == 0)
    report["passed"] = True
finally:
    report["container_logs"] = subprocess.run(["docker", "logs", name], capture_output=True, text=True).stderr[-6000:]
    subprocess.run(["docker", "stop", name], capture_output=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"task_id": args.task_id, "passed": report["passed"], "checks": len(report["checks"])}))
