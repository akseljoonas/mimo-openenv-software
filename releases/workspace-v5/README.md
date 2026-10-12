---
license: other
license_name: mixed-apache-2.0-and-mit
license_link: https://github.com/akseljoonas/mimo-openenv-software
language: [en]
tags: [openenv, reinforcement-learning, tool-use]
source_datasets:
  - XiaomiMiMo/MiMo-V2.6-RL-oss
  - ruv/metaharness-arena-tasks
configs:
  - config_name: default
    data_files:
      - split: train
        path: tasks.jsonl
---

# Fixed workspace reasoning and original MiMo repairs

A candidate curriculum of 32 public procedural data-workflow cases and two original MiMo code repairs. This is a preparation artifact, not evidence of a training or benchmark result. No model trials, ablations, private task probes or estimated benchmark scores are included.

## Why change the previous release

Our five-task run `bbb7a0a9dda9141d10f00d0b` completed 55 optimizer steps and scored 3/40 on Arena's private evaluation. The account's 6/40 leaderboard aggregate stayed unchanged because it keeps the best result in each domain across runs. Training logs cover only 38 of the 55 steps: 13 show mixed rewards and nonzero gradients. The previous 12-task run completed 84 steps, with 4 mixed-reward groups among 81 available logs, and scored 5/40. Increasing reward-bearing updates did not establish broader capability. The five-task release over-weighted a narrow training proxy; these observations do not prove a particular causal mechanism such as catastrophic forgetting.

Mapping training task ordinals to declared request order, the PYroMat lookup accounts for 7 of 13 observed mixed groups; the DTW task accounts for about 41% of logged step time. This mapping is inferred, since task-labelled model trajectories are not public. Fastavro has zero reward in all seven observed groups. The new candidate retains PYroMat and MRI-NUFFT unchanged, removes the other three from the previous request, and broadens the work practiced in the remaining slots.

The public leader `ruv` had an 8/40 aggregate on 12 October 2026, but individual runs scored 4, 4, 2 and 4 out of 40. Its latest run completed 276 steps; mean logged step time was about 26.6 seconds, versus 211.5 seconds in our five-task run. Its public task source offers short, deterministic, multi-file reasoning with exact component rewards. These are useful design properties, not evidence of a 20% single-run model or a proven path to a target score. Public dataset and source records name several runtime versions; the exact image used in its latest run has not been independently verified.

## Task selection and transport

The procedural generator and grader in `vendor/tasks.py` are copied byte-for-byte from [RuvNet/metaharness at 4657e5b](https://github.com/ruvnet/metaharness/blob/4657e5b82e124917b01d79ee5e9de41badb48fda/integrations/openenv-arena/arena_env/tasks.py), under its MIT license preserved in `vendor/LICENSE`. `provenance.json` records the complete revision and file hash. We selected all eight public families equally, at difficulties 1 and 2, using two predeclared seeds, 101 and 307. There was no model-based case selection. The families cover dependency impact and test selection, constrained scheduling, calibration, contact reconciliation, ledger reversals, constrained routing, access-policy auditing, and media timelines.

Each task ID fixes its family, difficulty and seed. Arena's per-episode seed does not change its inputs, so episodes in the same training group solve the same problem. On reset, the server writes three input files and instructions to `/workspace/repo`. The model uses the existing shell-action interface to read, calculate and write `answer.json`, then finishes. This is a new file-based transport; it differs from the upstream environment's virtual-file list/read/submit actions. The goal is to practice producing a concrete artifact with tools. Transfer from these bounded problems to Arena's private tasks remains unmeasured.

Full correct answers receive 1. The original procedural grader awards exact component credit, requires a substantive correct component, caps incomplete answers at 0.8, and rejects unknown keys. Empty, malformed, oversized and non-regular answer files receive zero. Expected answers are generated in protected server memory from the original input, so editing input files does not change the grading target. The grader and its source are inaccessible to the shell user. A terminal result is cached until reset. No rewards are added for verbosity, additional commands or presentation.

The two MiMo tasks are `format-code-task-000666` (PYroMat exact substance lookup) and `format-code-task-001926` (MRI-NUFFT density cell counts). Their original records, image digests, binary graders and existing budgets remain unchanged. Their provenance is [XiaomiMiMo/MiMo-V2.6-RL-oss at 639865f](https://huggingface.co/datasets/XiaomiMiMo/MiMo-V2.6-RL-oss/tree/639865fd3374018d6cb29b9fb82dd531406fcf5f), under Apache-2.0 and the licenses of the original task projects. They appear after the first and third blocks of eight procedural cases. This release is a mixed curriculum, not 34 original MiMo tasks.

## Runtime contract and consumers

Our adapter owns task reset, unprivileged shell execution and terminal artifact delivery. RuvNet's unchanged generator/grader owns procedural task content and rewards; XiaomiMiMo's original graders own the two repair rewards. Arena owns model loading, task scheduling, optimization, admission, dataset snapshotting and private evaluation. All three images use the same `ShellAction` and `ShellObservation` schema from our existing MiMo adapter. The new image derives from the immutable PYroMat image to reuse its pinned OpenEnv runtime and command runner, not to alter the original repair image.

The server requires no injected variables, files or secrets, runs `linux/amd64` on port 8000, and permits one session at a time. Shell commands run as UID 2000, time out after 60 seconds and return at most 12,000 bytes. There are 16 actions in each procedural episode; the sixteenth shell action executes before automatic grading. Reset discards prior workspace files. `answer.json` must be a regular file of at most 16,384 bytes; symbolic links and FIFOs are rejected. Missing answers are normal failures; unexpected infrastructure exceptions remain errors.

Procedural request ceilings are 120 seconds for reset, 300 for rollout, 30 for grading, 16 calls, 8,192 completion/observation tokens, 16,384 context tokens, 2 vCPUs, 16 GiB RAM and a 10 GiB writable workspace. These are configured ceilings, not measured model requirements or throughput forecasts. Original repair budgets stay at 180/1,200/120 seconds and 64 calls with 32,768 completion/context tokens. Arena determines actual optimizer steps within its four-hour allocation.

## Validation and release state

`verify_workflows.py` starts the image with the actual Docker command and speaks the OpenEnv WebSocket protocol. It verifies all 32 correct and incorrect episodes, original partial-credit behavior, fixed task identity across reset seeds, reset isolation, schema equality, protected grader files, malformed/oversized/non-regular answers, and final-action behavior. Correctness fixtures compute from actual input files through shell actions; they are not model outputs or training examples. The original MiMo tasks use the repository's unchanged `verify.py` repair checks.

The build context excludes validation fixtures and evidence. `vendor/tasks.py` contains upstream's reference function alongside its generator and grader; the entire file is protected from the agent, never exposed as a tool or observation. Its bytes are unchanged for reproducible attribution. `submission.json`, once generated, records immutable image digests. Publication, local correctness, Arena admission, training and private evaluation are separate states. The rolling 24-hour quota still applies. No recurring submission or message-board posting is part of this release.

## Prepared release, 12 October 2026

The new immutable image is `ghcr.io/akseljoonas/mimo-openenv-software@sha256:2a98ad8c3d9bb246d17de77d872b9e22cf4978b076100ca798edf90dd17bedad`, built from source revision `0b8d9e061cf8b11bb905f168ceb14b8de24028d8`. [Linux CI](https://github.com/akseljoonas/mimo-openenv-software/actions/runs/38230716679) passed 595 checks across all 32 procedural cases before publication. A fresh anonymous pull and replay of that exact digest also passed all 595 checks. Fresh tests of the two unchanged MiMo images passed 24 further checks. All three schemas match the submission request, and all three images were anonymously accessible. They total 1,485,090,141 compressed bytes when shared layers are counted once.

The first local prototype exposed an invalid-answer handling bug: a directory named `answer.json` caused an infrastructure error. The file reader was corrected to reject non-regular files before reading; both published-image validation runs include this regression check. The final source keeps the upstream generator and grader byte-identical.

`submission.json` is the prepared 34-task request. No Arena admission, training or private evaluation has been performed for this candidate. Passing 619 distinct procedural and MiMo checks validates the environment contract, not the probability of a target benchmark score.
