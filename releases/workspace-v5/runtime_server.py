"""OpenEnv adapter for reviewed TMax file-artifact tasks.

The public shell schema matches the previously published MiMo adapter. This
server must run inside its dedicated container: never execute it on the host.
"""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import subprocess
import tempfile
from typing import Literal
import uuid

from openenv.core.env_server import Action, Environment, Observation, State, create_app
from pydantic import Field

ROOT = Path("/opt/arena")
WORKSPACE = Path("/home/user")
AGENT_UID = 2000
GRADER_UID = 2001
MAX_OUTPUT = 8000
INTERFACE_REMINDER = '\n\nACTION FORMAT: Reply with exactly one JSON object: {"operation":"shell","command":"..."} or {"operation":"finish"}. Do not add prose, markdown fences, or schema fields such as additionalProperties. Escape double quotes inside command as \\" and represent line breaks as \\n. A complete valid example is {"operation":"shell","command":"python3 - <<\'PY\'\\nprint(\'ready\')\\nPY"}.'


class ShellAction(Action):
    operation: Literal["shell", "finish"] = Field(description="Run a bash command or finish and grade the artifacts.")
    command: str = Field(default="", max_length=16000, description="Bash command; each call starts in /home/user.")


class ShellObservation(Observation):
    task_id: str
    output: str = Field(max_length=12000)
    exit_code: int | None = None


def run_process(argv, *, cwd, uid, timeout=60, stdin=None):
    clean_env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8",
                 "HOME": "/home/user" if uid == AGENT_UID else "/tmp",
                 "PYTHONNOUSERSITE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    with tempfile.TemporaryFile() as output:
        proc = subprocess.Popen(argv, cwd=cwd, env=clean_env, stdin=stdin,
            stdout=output, stderr=subprocess.STDOUT, user=uid, group=uid,
            extra_groups=[], start_new_session=True)
        timed_out = False
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
        length = output.tell()
        output.seek(max(0, length - MAX_OUTPUT))
        text = output.read(MAX_OUTPUT).decode("utf-8", "replace")
    if length > MAX_OUTPUT:
        text = "[output truncated]\n" + text
    if timed_out:
        text += "\n[command timed out]"
    return {"output": text, "returncode": 124 if timed_out else proc.returncode}


class ArtifactEnvironment(Environment):
    def __init__(self):
        super().__init__()
        if os.geteuid() != 0 or not (ROOT / "container.marker").is_file():
            raise RuntimeError("This adapter runs only inside its dedicated container")
        self.bundles = {b["task_id"]: b for b in json.loads((ROOT / "bundles.json").read_text())}
        self._state = State()
        self.bundle = None
        self.terminal = None
        self.readonly_hashes = {}

    def reset(self, seed=None, episode_id=None, task_id=None, **kwargs):
        task_id = task_id or next(iter(self.bundles))
        if task_id not in self.bundles:
            raise ValueError("Unknown task_id")
        self.bundle = self.bundles[task_id]
        if WORKSPACE.is_symlink():
            WORKSPACE.unlink()
        elif WORKSPACE.exists():
            shutil.rmtree(WORKSPACE)
        WORKSPACE.mkdir(mode=0o755)
        os.chown(WORKSPACE, AGENT_UID, AGENT_UID)
        for name, content in self.bundle["files"].items():
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise ValueError("Unsafe fixture path")
            dest = WORKSPACE / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content)
            dest.chmod(0o644)
        for path in WORKSPACE.rglob("*"):
            os.chown(path, AGENT_UID, AGENT_UID)
        if self.bundle.get("setup"):
            with tempfile.TemporaryFile() as source:
                source.write(self.bundle["setup"].encode())
                source.seek(0)
                result = run_process(["python3", "-I", "-"], cwd=str(WORKSPACE),
                                     uid=AGENT_UID, timeout=90, stdin=source)
            if result["returncode"] != 0:
                raise RuntimeError("Initial fixture construction failed: " + result["output"])
        self.readonly_hashes = {}
        for name in self.bundle["readonly_files"]:
            path = WORKSPACE / name
            if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(WORKSPACE):
                raise ValueError("Immutable input path is invalid")
            self.readonly_hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        self._state = State(episode_id=episode_id or str(uuid.uuid4()), step_count=0)
        self.terminal = None
        return ShellObservation(task_id=task_id, reward=0.0, output=self.bundle["instruction"] +
            '\n\nWorkspace: /home/user. Inspect, edit and test with shell actions. '
            'Each shell call starts there and has a 60-second limit. '
            'Every reply must be exactly one JSON object, with no prose or code fences. '
            'For example: {"operation":"shell","command":"ls -la"}. '
            'Finish with {"operation":"finish"} when the required artifacts are ready.' + INTERFACE_REMINDER)

    def grade(self, verifier=None):
        # Grader scripts and source bundles are inaccessible to the learner UID.
        # Tests only parse artifacts; code-executing tests fail the offline audit.
        for name, expected in self.readonly_hashes.items():
            path = WORKSPACE / name
            if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(WORKSPACE) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                return 0.0, {"returncode": 1, "output": "An immutable source artifact was changed."}
        with tempfile.TemporaryDirectory(prefix="arena-grader-") as directory:
            root = Path(directory)
            root.chmod(0o700)
            os.chown(root, GRADER_UID, GRADER_UID)
            test = root / "test_artifacts.py"
            test.write_text(verifier or self.bundle["verifier"])
            test.chmod(0o600)
            os.chown(test, GRADER_UID, GRADER_UID)
            result = run_process(["python3", "-I", "-m", "pytest", "-q", "-p", "no:cacheprovider", str(test)],
                                 cwd=str(root), uid=GRADER_UID, timeout=90)
        if result["returncode"] not in (0, 1):
            raise RuntimeError("Verifier infrastructure failed: " + result["output"])
        return float(result["returncode"] == 0), result

    def step(self, action, timeout_s=None, **kwargs):
        if self.bundle is None:
            raise RuntimeError("reset is required")
        if self.terminal is not None:
            return self.terminal
        self._state.step_count += 1
        result = None
        if action.operation == "shell":
            result = run_process(["/bin/bash", "-c", action.command], cwd=str(WORKSPACE),
                                 uid=AGENT_UID, timeout=min(60, timeout_s or 60))
        if action.operation == "finish" or self._state.step_count >= 64:
            reward, result = self.grade()
            self.terminal = ShellObservation(task_id=self.bundle["task_id"], output="Artifact verification completed.",
                exit_code=result["returncode"], reward=reward, done=True)
            return self.terminal
        return ShellObservation(task_id=self.bundle["task_id"], output=result["output"] + INTERFACE_REMINDER,
                                exit_code=result["returncode"], reward=0.0)

    @property
    def state(self):
        return self._state


app = create_app(ArtifactEnvironment, ShellAction, ShellObservation,
                 env_name="tmax_artifacts", max_concurrent_envs=1)
