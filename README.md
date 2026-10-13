# TMax artifact environments

This branch prepares a collection of fictional artifact tasks generated through [TMax](https://github.com/hamishivi/tmax) and reviewed with independent calculations and artifact checks. The collection contains seven tasks in office work, finance, and media.

Each episode provides source files under `/home/user`. A model uses shell commands to inspect data and create requested artifacts. The OpenEnv action is `{"operation":"shell","command":"..."}` or `{"operation":"finish"}`. Grading checks the resulting artifacts and preservation of protected source inputs.

The existing GitHub Actions workflow is retained without modification. Its historical `workspace-v5` release path builds this branch's code, validates the actual server protocol, and publishes a commit-specific container tag. The branch content and source revision identify the release. CI protocol checks do not claim benchmark performance or replace local artifact-grader validation.

The published source and image contain no reference solution scripts, model transcripts, evaluation holdouts, or credentials. Source code is licensed under Apache-2.0; dependencies retain their licenses.

## Tasks

| Task | Domain |
| --- | --- |
| `finance-amortization-review` | finance and economics |
| `finance-cashflow-scenarios` | finance and economics |
| `finance-invoice-discount` | finance and economics |
| `media-caption-localization` | media and content production |
| `office-chart-rebuild` | office and white-collar work |
| `office-document-assembly` | office and white-collar work |
| `office-workbook-repair` | office and white-collar work |

`releases/workspace-v5/release_manifest.json` records the selected task IDs and artifact hashes. `generation_provenance.json` records the public generator/model revisions and fictional fixture origin. `requirements.txt` pins the complete recorded Python dependency set.
