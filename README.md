---
license: apache-2.0
language:
  - en
tags:
  - openenv
  - reinforcement-learning
  - software-engineering
source_datasets:
  - XiaomiMiMo/MiMo-V2.6-RL-oss
configs:
  - config_name: default
    data_files:
      - split: train
        path: tasks/*.json
---

# MiMo software engineering for OpenEnv

An OpenEnv adapter for eight software engineering tasks from [XiaomiMiMo/MiMo-V2.6-RL-oss](https://huggingface.co/datasets/XiaomiMiMo/MiMo-V2.6-RL-oss/tree/639865fd3374018d6cb29b9fb82dd531406fcf5f). Each task retains its original problem statement, repository image, test patch, test command and binary reward: **1 if the original tests exit successfully, 0 otherwise**. Infrastructure errors are reported as errors. No LLM judge or external service credentials are used.

The tasks cover Python and JavaScript library repairs. `tasks.jsonl` lists task identities and immutable upstream images; `tasks/` contains the original eight task records. Selection favored smaller images and self-contained tests. This is a small, non-random subset, not a reproduction of MiMo training or an estimate of general software engineering ability.

Source: https://github.com/akseljoonas/mimo-openenv-software

Dataset: https://huggingface.co/datasets/akseljoonas/mimo-openenv-software

## Runtime contract

Each task has a separate public `linux/amd64` image tagged `ghcr.io/akseljoonas/mimo-openenv-software:TASK_ID-v2`. The image starts its own OpenEnv server on port 8000 without mounted files, secrets or additional environment variables. Use an OpenEnv WebSocket session at `/ws`: `reset` accepts `task_id`; `step` accepts `{"operation":"shell","command":"..."}` or `{"operation":"finish"}`. Standalone HTTP `/reset` and `/step` are stateless in the pinned OpenEnv release.

Reset restores the repository snapshot. Shell actions start in the task's original working directory, run as UID 2000, last at most 60 seconds, and return at most 12,000 output bytes. `finish` invokes Xiaomi's original verifier and returns `done: true`; reaching 64 actions also grades. A terminal session returns its cached verdict until reset. Tests are installed only while grading. All runtime verifier commands and patch writes also run as UID 2000; the server and stored task record are inaccessible to that user. This is not a security boundary against every possible reward exploit in arbitrary upstream repositories.

Build preparation uses Xiaomi's existing Git-history stripping routine, then its setup assertion, before snapshotting the repository. This removes reachable future fixes present in some original images. Existing task files and grading code are not rewritten. The adapter has its own Python runtime so task dependencies remain intact.

## Pinned sources

- Dataset: `639865fd3374018d6cb29b9fb82dd531406fcf5f` (Apache-2.0).
- [MiMo-Agent](https://github.com/XiaomiMiMo/MiMo-Agent/tree/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c): `467f0a19016f0ac4d63b8d17a1f0da9ba07f232c` (MIT).
- [OpenEnv](https://github.com/meta-pytorch/OpenEnv/tree/86a180ede21e044f7929b9a7783ad83aa67d83a3): `86a180ede21e044f7929b9a7783ad83aa67d83a3`, Arena's required revision.
- Python runtime base and task images are pinned by digest. Python packages are pinned in `requirements.lock`.

The original code-task runner is Xiaomi's `recipes/code/mimoagent_runner.py` at [verl revision a2ad9f6](https://github.com/XiaomiMiMo/verl/tree/a2ad9f6160b03ff2d47e59832bfb6b289f37c917). It constructs the dataset environment, runs an agent, and calls `calculate_reward`. This adapter replaces that agent transport with OpenEnv while reusing the published `OpenSourceCodeEnvironment` grading implementation. XiaomiMiMo owns the upstream task/verifier; this repository owns only the OpenEnv adapter and selection. Upstream project licenses remain applicable inside each image.

## Build and verify

Install the pinned OpenEnv CLI. For a row in `tasks.jsonl`:

```sh
export DOCKER_DEFAULT_PLATFORM=linux/amd64
openenv build -t ghcr.io/akseljoonas/mimo-openenv-software:TASK_ID-v2 \
  --build-arg TASK_ID=TASK_ID --build-arg TASK_IMAGE=SOURCE_IMAGE_DIGEST
python verify.py IMAGE TASK_ID --output evidence/TASK_ID.json
```

`verify.py` runs the image with 2 CPUs and 16 GiB, checks readiness and all six OpenEnv endpoint checks, then replays real WebSocket episodes: unsolved reward 0, stable terminal reward, protected verifier, absent future Git refs, and reset isolation. The Django task additionally uses `--solution solutions/friendship.py` to check reward 1 and restoration to reward 0. Reference solutions are excluded from images. Reports document the checks actually performed; they do not establish Arena admission, training or private evaluation results.

The `Publish images` GitHub workflow builds, tests and publishes the selected images with short-lived GitHub Actions registry authentication. No Hugging Face token is included in this repository or its artifacts. Arena submission requires a separate human approval and is not triggered by the build workflow.

## Status

The initial eight images passed local endpoint and episode checks, with a Django reference repair scoring 1. Revision v2 addresses a verifier privilege issue found in final review; rebuild and regression verification are in progress. Do not submit v1 images. No Arena submission or training run has been started.
