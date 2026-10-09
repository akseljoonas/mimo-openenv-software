"""OpenEnv transport for original MiMo code and terminal task graders."""

import json
import os
from pathlib import Path
import shutil
import shlex
import signal
import subprocess
import tarfile
import tempfile
from typing import Literal
import uuid

from mimoagent.environments.datasets.opensource_code import OpenSourceCodeEnvironment
from mimoagent.environments.local import LocalEnvironment
from openenv.core.env_server import Action, Environment, Observation, State, create_app
from pydantic import Field
from terminal import TerminalBenchVerifier


ROOT = Path(__file__).resolve().parent
INSTANCE = json.loads((ROOT / "instance.json").read_text())
WORKSPACE = Path(INSTANCE["cwd"])
AGENT_UID = 2000
OUTPUT_LIMIT = 12000


class ShellAction(Action):
    operation: Literal["shell", "finish"] = Field(description="Run a bash command or finish and grade the repository.")
    command: str = Field(default="", max_length=16000, description="Bash command; each call starts in the task repository.")


class ShellObservation(Observation):
    task_id: str
    output: str = Field(max_length=16000)
    exit_code: int | None = None


class VerifierExecution(LocalEnvironment):
    """Keep upstream verifier operations in the container, with bounded processes."""

    def __init__(self, *, privileged=False, **kwargs):
        super().__init__(**kwargs)
        self.privileged = privileged

    def execute(self, command, cwd="", timeout=None):
        return run_command(command, cwd or str(WORKSPACE), timeout or 120,
                           agent=not self.privileged)

    def copy_to(self, src_path, dest_path, **kwargs):
        with open(src_path, "rb") as source:
            result = run_command("cat > " + shlex.quote(dest_path), str(WORKSPACE),
                                 120, agent=not self.privileged, stdin=source)
        if result["returncode"] != 0:
            raise RuntimeError("Verifier file transfer failed")


def make_verifier(*, privileged=False):
    execution = VerifierExecution(cwd=str(WORKSPACE), privileged=privileged)
    if INSTANCE["dataset_type"] == "opensource-code":
        return OpenSourceCodeEnvironment(execution, INSTANCE)
    if INSTANCE["dataset_type"] == "terminal_bench":
        return TerminalBenchVerifier(execution, INSTANCE)
    raise ValueError("Unsupported MiMo dataset type")


def run_command(command, cwd, timeout, *, agent, stdin=None):
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    if agent:
        env.update(HOME="/home/arena-agent", USER="arena-agent", LOGNAME="arena-agent")
    # A file avoids retaining unbounded command output in server memory.
    with tempfile.TemporaryFile() as output:
        proc = subprocess.Popen(
            ["/bin/bash", "-c", command], cwd=cwd, env=env,
            stdin=stdin, stdout=output, stderr=subprocess.STDOUT, start_new_session=True,
            user=AGENT_UID if agent else None,
            group=AGENT_UID if agent else None,
            extra_groups=[] if agent else None,
        )
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
        output.seek(max(0, length - OUTPUT_LIMIT))
        text = output.read(OUTPUT_LIMIT).decode("utf-8", "replace")
    if length > OUTPUT_LIMIT:
        text = "[output truncated to final 12000 bytes]\n" + text
    if timed_out:
        text += "\n[command timed out]"
    return {"output": text, "returncode": 124 if timed_out else proc.returncode}


class MiMoEnvironment(Environment):
    def __init__(self):
        super().__init__()
        self._state = State()
        self.verifier = None
        self.terminal = None

    def reset(self, seed=None, episode_id=None, task_id=None, **kwargs):
        if task_id not in (None, INSTANCE["instance_id"]):
            raise ValueError("This image does not contain that task_id")
        if WORKSPACE not in (Path("/testbed"), Path("/workspace/repo"), Path("/app")):
            raise RuntimeError("Unsupported workspace in pinned task")
        if WORKSPACE.exists():
            shutil.rmtree(WORKSPACE)
        with tarfile.open(ROOT / "workspace.tar") as archive:
            archive.extractall(WORKSPACE.parent, filter="fully_trusted")
        subprocess.run(["chown", "-R", f"{AGENT_UID}:{AGENT_UID}", str(WORKSPACE)], check=True)
        self.verifier = make_verifier()
        self.verifier.setup_environment()
        self._state = State(episode_id=episode_id or str(uuid.uuid4()), step_count=0)
        self.terminal = None
        instruction = (
            INSTANCE["problem_statement"]
            + f"\n\nRepository: {WORKSPACE}. Use shell actions to inspect, edit, and test it. "
            'Return {"operation":"finish"} when ready for the original MiMo tests. '
            "Each shell call starts in the repository; use cd within a command as needed. "
            "Commands time out after 60 seconds and output is truncated."
        )
        return ShellObservation(task_id=INSTANCE["instance_id"], output=instruction, reward=0.0)

    def step(self, action, timeout_s=None, **kwargs):
        if self.verifier is None:
            raise RuntimeError("reset is required before step")
        if self.terminal is not None:
            return self.terminal
        self._state.step_count += 1
        if action.operation == "finish" or self._state.step_count >= 64:
            reward, output, info = self.verifier.calculate_reward(timeout=INSTANCE["verifier_timeout_sec"])
            if info.get("error_category") or info.get("transport_error") or "verifier_returncode" not in info:
                raise RuntimeError("MiMo verifier infrastructure failed; no valid reward")
            self.terminal = ShellObservation(
                task_id=INSTANCE["instance_id"], output="Original MiMo verifier completed.",
                exit_code=info["verifier_returncode"], reward=float(reward), done=True,
            )
            return self.terminal
        result = run_command(action.command, str(WORKSPACE), min(60, timeout_s or 60), agent=True)
        return ShellObservation(task_id=INSTANCE["instance_id"], output=result["output"], exit_code=result["returncode"], reward=0.0)

    @property
    def state(self):
        return self._state


app = create_app(MiMoEnvironment, ShellAction, ShellObservation, env_name="mimo_software", max_concurrent_envs=1)
