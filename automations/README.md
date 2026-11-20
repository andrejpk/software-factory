---
title: Software Factory on GitHub Copilot automations
description: Experimental port of the Software Factory loop to Copilot cloud automations and gh-aw, with no custom backend.
---

## Overview

This folder re-implements the Software Factory loop (see the root [SPEC.md](../SPEC.md)) on
GitHub-native pieces only:

* **Copilot cloud automations** (public preview) run the coordinating "lead engineer" roles.
* **Copilot cloud agent** writes code; **Copilot code review** reviews it.
* **GitHub Agentic Workflows (gh-aw)** runs the optional hve-core `/review` workflow.
* **APM (Agent Package Manager)** links reusable skills and agents from upstream repos with
  pinned revisions.

Nothing runs on your machine and nothing in `backend/` or `frontend/` is used. Those folders are
the original local app and are left untouched as the legacy implementation.

> [!IMPORTANT]
> This is an experiment. Read [GAPS.md](GAPS.md) before relying on it. Two steps still need a
> person in the loop: starting a Copilot session and waking Copilot for fixes.

## Architecture

```mermaid
flowchart LR
  BRD["BRD issue (sf:brd)<br/>+ docs/BRD.md"] -- "label sf:plan" --> P[sf-planner]
  P -- "sf:task issues<br/>(sub-issues, deps)" --> D[sf-dispatcher]
  D -- "assign Copilot<br/>(WIP 2)" --> CA[Copilot cloud agent]
  CA -- "draft PR" --> S[sf-pr-shepherd]
  S -- "ready, request review,<br/>@copilot fixes (max 3)" --> CA
  S -- "gated squash merge" --> M[(main)]
  M -- "issue closed" --> D
  R[sf-status-reporter] -. "daily" .-> ST["Status issue (sf:status)"]
```

| Automation | Prompt | Triggers | Job |
| --- | --- | --- | --- |
| `sf-planner` | [planner.md](prompts/planner.md) | issue labeled `sf:plan`, manual | Splits the BRD into self-contained `sf:task` sub-issues with acceptance criteria and dependencies |
| `sf-dispatcher` | [dispatcher.md](prompts/dispatcher.md) | issue labeled/closed, PR merged, hourly, manual | Promotes tasks whose dependencies are done to `sf:ready` and assigns Copilot up to the WIP limit |
| `sf-pr-shepherd` | [shepherd.md](prompts/shepherd.md) | PR ready/synchronize/merge conflict, review requested/submitted, CI failed, hourly, manual | Marks drafts ready, releases held CI runs, requests Copilot review, routes findings back with `@copilot`, merges when gates pass |
| `sf-status-reporter` | [reporter.md](prompts/reporter.md) | daily, manual | Rewrites the `sf:status` issue with a pipeline summary |

Every prompt is prefixed with [_conventions.md](prompts/_conventions.md), which defines the label
state machine, hidden markers, policy constants (WIP 2, remediation cap 3) and hard rules.

### Label state machine

`sf:brd` → `sf:plan` → `sf:planned` on the BRD issue. Each `sf:task` issue moves through
Todo (no status label) → `sf:ready` → `sf:in-progress` → `sf:in-review` → `sf:done`, with
`sf:blocked` whenever a person must act. Labels stand in for the original Projects v2 Status field
because automations have no Projects v2 tool.

## Install

Prerequisites: a **private or internal** repository (cloud automations don't run on public repos),
a Copilot plan with cloud agent and automations enabled, and `gh` authenticated as the account the
automations should act as and bill.

```powershell
gh api user --jq .login                       # confirm the identity first
./automations/install.ps1 -Repo owner/repo    # create or update automations and sf:* labels
./automations/install.ps1 -Repo owner/repo -Disable   # pause all of them
```

`install.ps1` is idempotent. It reads [definitions/](definitions/), concatenates the prompt files,
and creates or updates each automation by name through the automations REST API
(`/agents/repos/{owner}/{repo}/automations`, API version `2026-03-10`). Each definition sets a
per-run AI credit limit (`run_limit_credits`, 30 for each, the API minimum) and a daily limit
(`daily_limit_credits`, 30 to 100). Automations
are stored outside Git, so these files are the source of truth: edit them and re-run the script.

Then copy the files in [template/](template/) into the target repository (see
[Provenance and updates](#provenance-and-updates)), add a BRD as `docs/BRD.md` and as an issue
labeled `sf:brd`, and add `sf:plan` to that issue.

## Provenance and updates

Reusable agent primitives are **linked, not copied**. [template/](template/) holds the files the
target repository needs:

| File | Purpose |
| --- | --- |
| [apm.yml](template/apm.yml) | Declares upstream skills and agents, tracking `main` |
| [apm.lock.yaml](template/apm.lock.yaml) | Pins the exact commits (`resolved_commit`) and content hashes |
| [.github/workflows/pr-review.md](template/.github/workflows/pr-review.md) | hve-core's gh-aw review workflow, added with `gh aw add ...@<sha>`; `source:` records the origin. Compile with `gh aw compile` |
| [.github/workflows/sf-deps-update.yml](template/.github/workflows/sf-deps-update.yml) | Weekly: `apm install --frozen`, `apm update --yes`, `gh aw update`, then a PR |
| [THIRD_PARTY_NOTICES.md](template/THIRD_PARTY_NOTICES.md) | Attribution for linked sources |
| [BRD.md](template/BRD.md) | The tiny BRD used in the live run |

Linked sources:

| Source | Item | Used by |
| --- | --- | --- |
| microsoft/hve-core | `skills/shared/untrusted-content-boundary` | every automation (`_conventions.md`) |
| microsoft/hve-core | `skills/project-planning/backlog-management`, `backlog-plan` | planner |
| microsoft/hve-core | `skills/coding-standards/code-review` | gh-aw `pr-review` |
| microsoft/hve-core | `agents/project-planning/brd-builder.agent.md` | BRD refinement in the Copilot app or VS Code |
| microsoft/hve-core | `.github/workflows/pr-review.md` (gh-aw) | optional `/review`; shepherd reads `needs-revision` |
| andrejpk/andrej-agent-kit | `plugins/gh-orchestrator` skills `orchestrate`, `issue-intake` | interactive orchestration from the Copilot app |

`apm install` deploys skills to `.agents/skills/` and agents to `.github/agents/`. Treat that
output as generated. To change an upstream item, contribute upstream or override it in our own
prompts; do not edit the generated files.

Update flow:

1. `sf-deps-update.yml` runs weekly or on demand. It restores the locked state, runs
   `apm update --yes` and `gh aw update` (a 3-way merge that keeps local edits such as our
   skill-path retargeting in `pr-review.md`), recompiles, and opens a PR.
2. Opening that PR requires a `SF_DEPS_TOKEN` secret (a fine-grained PAT with contents, pull
   requests and workflows write), because the default `GITHUB_TOKEN` cannot write to
   `.github/workflows`. Without the secret the workflow only reports the diff.
3. Generate `apm.lock.yaml` on Linux with the pinned `apm-cli` version. A lockfile produced on
   Windows has different content hashes and fails `apm install --frozen` in CI.

Dependabot and Renovate don't understand `apm.yml`, so the scheduled workflow is the update path.

## Live run

The loop ran end to end in the private sandbox
[andrejpk/sf-automation-sandbox](https://github.com/andrejpk/sf-automation-sandbox) on a
three-task CLI BRD. One task completed the whole cycle, including one remediation round, and
merged as PR #5. [GAPS.md](GAPS.md) records each step and where a person had to intervene.
