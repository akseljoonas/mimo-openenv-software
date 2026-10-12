"""File-based transport for the attributed public procedural curriculum.

The pinned MiMo base supplies the existing shell schema and unprivileged command
runner. This module owns only procedural task identity, reset and artifact grading.
"""
import errno
import json
import os
from pathlib import Path
import shutil
import stat
import uuid

from openenv.core.env_server import Environment, State, create_app
from server import AGENT_UID, ShellAction, ShellObservation, run_command
from vendor.tasks import grade, make_task

ROOT = Path(__file__).resolve().parent
WORKSPACE = Path("/workspace/repo")
CASES = json.loads((ROOT / "cases.json").read_text())
MAX_ACTIONS = 16
MAX_ANSWER_BYTES = 16384


def read_answer():
    """Read bounded regular JSON only; never follow agent-controlled links."""
    try:
        fd = os.open(WORKSPACE / "answer.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except (FileNotFoundError, IsADirectoryError):
        return None
    except OSError as error:
        # An agent-created symlink is an invalid answer, not a server fault.
        if error.errno == errno.ELOOP:
            return None
        raise
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_ANSWER_BYTES:
            return None
        raw = os.read(fd, MAX_ANSWER_BYTES + 1)
    finally:
        os.close(fd)
    if len(raw) > MAX_ANSWER_BYTES:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError):
        return None


class WorkflowEnvironment(Environment):
    def __init__(self):
        super().__init__()
        self._state = State()
        self.task = None
        self.case_id = None
        self.terminal = None

    def reset(self, seed=None, episode_id=None, task_id=None, **kwargs):
        # Identity completely determines the case. Arena's per-episode seed must
        # not change the question within a GRPO group for this fixed curriculum.
        case_id = task_id or next(iter(CASES))
        if case_id not in CASES:
            raise ValueError("Unknown fixed workflow task_id")
        case = CASES[case_id]
        task = make_task(case["family"], case["seed"], case["difficulty"])
        if WORKSPACE.is_symlink():
            WORKSPACE.unlink()
        elif WORKSPACE.exists():
            shutil.rmtree(WORKSPACE)
        WORKSPACE.mkdir(mode=0o755)
        for name, content in task["files"].items():
            path = WORKSPACE / name
            path.write_text(content)
            os.chown(path, AGENT_UID, AGENT_UID)
        instruction = (
            task["prompt"]
            + '\n\nWorkspace: /workspace/repo. Use shell actions to read the files and compute the result; '
            'Python 3 and its standard library are available. Write the requested JSON object to '
            'answer.json, then send {"operation":"finish"}. Each shell command starts in the workspace. '
            'There are 16 actions including finish; commands have a 60-second limit. '
            'Only answer.json is graded, against the original input data. It must be a regular UTF-8 JSON '
            'file of at most 16384 bytes. Correct complete output earns 1; exact correct substantive '
            'components can earn partial credit; missing, invalid or empty answers earn 0.'
        )
        (WORKSPACE / "INSTRUCTIONS.txt").write_text(instruction)
        os.chown(WORKSPACE / "INSTRUCTIONS.txt", AGENT_UID, AGENT_UID)
        os.chown(WORKSPACE, AGENT_UID, AGENT_UID)
        self.task, self.case_id = task, case_id
        self._state = State(episode_id=episode_id or str(uuid.uuid4()), step_count=0)
        self.terminal = None
        return ShellObservation(task_id=case_id, output=instruction, reward=0.0)

    def step(self, action, timeout_s=None, **kwargs):
        if self.task is None:
            raise RuntimeError("reset is required before step")
        if self.terminal is not None:
            return self.terminal
        self._state.step_count += 1
        # The last shell action still executes before automatic final grading.
        result = None
        if action.operation == "shell":
            result = run_command(action.command, str(WORKSPACE), min(60, timeout_s or 60), agent=True)
        if action.operation == "finish" or self._state.step_count >= MAX_ACTIONS:
            self.terminal = ShellObservation(
                task_id=self.case_id, output="Workflow artifact verifier completed.",
                exit_code=0, reward=grade(self.task, read_answer()), done=True,
            )
            return self.terminal
        return ShellObservation(task_id=self.case_id, output=result["output"],
                                exit_code=result["returncode"], reward=0.0)

    @property
    def state(self):
        return self._state


app = create_app(WorkflowEnvironment, ShellAction, ShellObservation,
                 env_name="workspace_workflows", max_concurrent_envs=1)
