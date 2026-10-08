# MiMo experiment series

The accepted control is `mimo-software-v2-20261008`, run `03bfc81de59cf3e53b9e05d0`: eight tasks, 1,200-second rollouts, 32,768 completion/context tokens and 64 actions. The adapter and image digests stay fixed at the validated v2 implementation. Xiaomi's original test patch, command and binary reward remain unchanged. Arena owns policy initialization, optimizer settings, GRPO sampling and private evaluation; these requests do not control them.

Arena's [published contract](https://openenvarena-arena.hf.space/AGENTS.md) permits one accepted submission per account per rolling 24 hours. The baseline consumed the slot until October 9, 2026 at 15:49:14 UTC. Check the live submission `slot` before every later attempt. Do not use another account, alternate identity or duplicate request to evade this limit.

## First batch: five prepared candidates

- `rollout-600`: reduce only each task's rollout wall limit to 600 seconds; test throughput versus truncation.
- `rollout-2400`: increase only that limit to 2,400 seconds; test whether longer repairs recover useful successes. Skip or replace if baseline episodes never approach 1,200 seconds.
- `completion-16k`: reduce only the completion budget to 16,384 tokens; context capacity remains 32,768. Arena charges later observations to the completion budget too.
- `python-only`: retain the five Python tasks, preserving relative order and all task budgets.
- `javascript-only`: retain the three JavaScript tasks, preserving relative order and all task budgets.

Every candidate includes an exact digest-pinned request and hash in `queue.json`. None is claimed to have trained yet. Task subsets also change exposure frequency, so their results cannot isolate programming language from repetition or task difficulty. No identical training seed is available in the request contract; one run per variant is exploratory evidence, not a statistically controlled performance estimate.

## Observe, decide, submit

Run `monitor.py --output SNAPSHOT.json` with Python containing `requests` and `huggingface_hub`. It reads the existing HF CLI login in memory, authenticates only Arena GETs, and reads Trackio anonymously. It never submits. Keep timestamped snapshots outside the image; publish concise findings and final scores after review.

Use Arena lifecycle and events for launch, retry, failure and completion. Follow each returned dashboard's project/run identity, query the metric names its Trackio summary actually lists, and retain full curves. Trackio HTTP errors, error envelopes, missing metrics and empty curves mean unavailable data, never zero. Simulation records do not count as GPU training or benchmark results.

Before choosing a candidate, compare reward mean and dispersion, loss, gradient norm, completion lengths, step wall time, retries and completed optimizer steps where actually logged. Inspect episode/task logs before claiming why a task succeeded or failed. Task order alone is insufficient to attribute metrics when retries or missing groups could change the mapping. Constant rewards can yield little learning signal; more training reward can also reflect overfitting or a reward flaw, so inspect the evidence before selecting a curriculum.

Use completed Arena private-evaluation scores as the outcome, with software-domain and all-domain results reported separately. The leaderboard retains each domain's best across runs; this aggregate is not one model's joint score. Retain each run's own scores, failed tasks, configuration, dataset revision and image identities. Five private tasks per domain give coarse, noisy comparisons. Never infer general improvement from a single favorable training curve.

When a slot is available, choose one informative validated request based on the observed results, record the reason in `queue.json`, confirm public image/data availability and quota, then submit using the cached HF login in memory. Save the response and re-read its status. For ambiguous network outcomes, inspect the exact submission ID before retrying unchanged. An accepted admission failure can consume the daily slot. Never blindly retry with a new ID.

For subsequent batches, prepare four or five variants informed by completed runs. Keep changes attributable and validate any new runtime/image through real episodes before publishing. Upload to Hugging Face with `hf upload`, not browser automation. Do not publish credentials, modify unrelated projects, post to the message board or send messages to other people.
