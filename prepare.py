"""Prepare the upstream image to meet MiMo's documented image contract."""
import json
from pathlib import Path
import subprocess
import tarfile

from mimoagent.environments.datasets.opensource_code import OpenSourceCodeEnvironment
from server import VerifierExecution

root = Path("/opt/arena")
instance = json.loads((root / "instance.json").read_text())
cwd = Path(instance["cwd"])
env = OpenSourceCodeEnvironment(VerifierExecution(cwd=str(cwd)), instance)
base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=cwd, text=True).strip()
if not env._strip_future_commits(base):
    raise RuntimeError("Upstream history stripping failed")
env.setup_environment()
with tarfile.open(root / "workspace.tar", "w") as archive:
    archive.add(cwd, arcname=cwd.name)
print(json.dumps({"task_id": instance["instance_id"], "base_commit": base, "history_checked": True}))
