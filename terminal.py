"""Run the original MiMo terminal tests and consume their reward-file contract."""
import base64
import json
import os
from pathlib import Path, PurePosixPath
import shutil


class TerminalBenchVerifier:
    """Materialize immutable upstream tests only after the rollout has finished."""

    def __init__(self, execution, instance):
        self.execution = execution
        self.instance = instance
        encoded = json.loads(instance["tests_files"])
        self.files = {}
        for name, value in encoded.items():
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Invalid original grader path")
            self.files[name] = base64.b64decode(value, validate=True)
        if "test.sh" not in self.files or instance["cwd"] != "/app":
            raise ValueError("Unsupported terminal task contract")

    def setup_environment(self):
        if not Path("/app").is_dir() or Path("/tests").exists():
            raise RuntimeError("Terminal workspace or hidden-test isolation invalid")

    def calculate_reward(self, timeout):
        tests = Path("/tests")
        logs = Path("/logs/verifier")
        if tests.exists():
            raise RuntimeError("Original grader already materialized")
        logs.parent.mkdir(exist_ok=True)
        if logs.exists():
            shutil.rmtree(logs)
        logs.mkdir(mode=0o700)
        os.chown(logs, 2000, 2000)
        try:
            tests.mkdir(mode=0o755)
            for name, content in self.files.items():
                target = tests / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                target.chmod(0o644)
            # Keep interpreter startup outside the writable task workspace.
            # The original scripts address /app and /tests explicitly.
            result = self.execution.execute("bash /tests/test.sh", cwd="/", timeout=timeout)
            reward_file = logs / "reward.txt"
            # Pytest collection errors (for example an agent's syntax error)
            # are ordinary failed solutions when the original script writes 0.
            if result["returncode"] not in range(6) or not reward_file.is_file() or reward_file.is_symlink():
                raise RuntimeError("Original terminal verifier did not produce a valid verdict")
            value = reward_file.read_text().strip()
            if value not in ("0", "1"):
                raise RuntimeError("Original terminal reward is outside its binary contract")
            if value == "1" and result["returncode"] != 0:
                raise RuntimeError("Successful terminal reward contradicts the verifier exit status")
            return float(value), result["output"], {"verifier_returncode": result["returncode"]}
        finally:
            if tests.exists():
                shutil.rmtree(tests)
            if logs.exists():
                shutil.rmtree(logs)
