"""Prepare the upstream image to meet MiMo's documented image contract."""
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

from server import make_verifier

root = Path("/opt/arena")
instance = json.loads((root / "instance.json").read_text())
cwd = Path(instance["cwd"])
dependencies = json.loads((root / "task-dependencies.json").read_text()).get(instance["instance_id"], [])
if dependencies:
    subprocess.run(["python3", "-m", "pip", "install", "--no-cache-dir", "--no-deps", *dependencies], check=True)
env = make_verifier(privileged=True)
base = None
if instance["dataset_type"] == "opensource-code":
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=cwd, text=True).strip()
    if not env._strip_future_commits(base):
        raise RuntimeError("Upstream history stripping failed")
elif list(cwd.rglob(".git")):
    raise RuntimeError("Frozen terminal task unexpectedly includes Git metadata")
env.setup_environment()
with tarfile.open(root / "workspace.tar", "w") as archive:
    archive.add(cwd, arcname=cwd.name)
shutil.rmtree(cwd)
print(json.dumps({"task_id": instance["instance_id"], "base_commit": base, "history_checked": True}))
