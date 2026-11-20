---
title: Gaps versus the original Software Factory
description: What the Copilot automations port loses or changes compared with the local app in SPEC.md, with evidence from a live run.
---

## Summary

The loop **runs** on GitHub-native pieces with no custom backend. The current (v2) design is
event-driven. Stages hand off only through labels, PRs and reviews. No automation assigns
Copilot or `@mentions` it, and the implementer automation writes the code itself. In
[andrejpk/sf-gh-tier](https://github.com/andrejpk/sf-gh-tier), three task PRs merged through
the chain, including one review → fix → re-review cycle. Only **one human step** remains:
releasing held CI runs on agent pushes. See [v2 live run](#v2-live-run-event-driven).

The first design (v1, below) assigned Copilot cloud agent and woke it with `@copilot`. It ran
end to end once ([sandbox PR #5](https://github.com/andrejpk/sf-automation-sandbox/pull/5)),
but a person had to step in at three points that the original backend handles in code:

1. **Starting Copilot sessions.** When an automation assigns Copilot to an issue, the session
   doesn't start. This happened on both tasks (#2, #3).
2. **Waking Copilot for fixes.** Copilot ignores an `@copilot` comment written by an automation.
   The same comment from a person started a session within 25 seconds.
3. **Releasing held CI runs and requesting Copilot review.** Neither automation tool works
   for these, although the same REST calls work for a user.

Enforcement also moves from service code (`gates.py`) to prompt text. And there is no
first-party place to watch or steer the factory. That's the UI gap, covered below.

## v2 live run (event-driven)

Repo: [andrejpk/sf-gh-tier](https://github.com/andrejpk/sf-gh-tier) (private, personal
automations acting as `andrejpk`). BRD: a multiplayer tier-list party game, planned into
tasks #3–#7 with dependency lists.

| Step | Trigger → action | Evidence | Human? |
| --- | --- | --- | --- |
| Review | `sf:review` label → `sf-reviewer` posts a COMMENT review with `<!-- sf:review verdict=… -->` | PR #8 clean; PR #10 findings (count 1) | No |
| Gate and merge | review submitted → `sf-shepherd` checks verdict, CI, head SHA; merges with an evidence comment | PR #8 (7e79baa), [PR #9](https://github.com/andrejpk/sf-gh-tier/pull/9), [PR #10](https://github.com/andrejpk/sf-gh-tier/pull/10) (fac4b1c) merged | No |
| Dispatch next | `issue_closed` → `sf-dispatcher` labels ready tasks `sf:in-progress` (WIP 2, dependencies respected) | #4 and #5 started after #3; #6 waited for #5 and started after it; #7 waits for #6 | No |
| Implement | `sf:in-progress` → `sf-implementer` writes code with `report_progress`, opens the PR, labels `sf:pr` + `sf:review` | PRs #9 and #10 opened with no assignment and no `@copilot` (≈15 credits per task) | No |
| Fix | shepherd posts findings + `sf:fix` → implementer fix mode pushes to the PR head and relabels `sf:review` | PR #10: fix pushed 18:13, clean re-review 18:17 | No |
| Release held CI | — | Agent pushes produce `action_required` runs. `retry_workflow_run` returns 409. `gh run rerun` as a user works | **Yes** |
| Stand-alone issue | Person opens an issue labelled `sf:task` with no dependencies → dispatcher → implementer → reviewer → shepherd | [#12](https://github.com/andrejpk/sf-gh-tier/issues/12) → [PR #13](https://github.com/andrejpk/sf-gh-tier/pull/13) merged; the shepherd added the missing `Closes #12` | Held CI only |
| Feedback triage | Person labels a feedback issue `sf:triage` → triager files `sf:backlog` sub-issues (bug, enhancement or feature) and posts product questions; a person promotes with `sf:task` or `sf:plan` | [#15](https://github.com/andrejpk/sf-gh-tier/issues/15) → #16, #17, #18 (enhancements); the early-end/timer item came back as questions, not a guessed issue | No (triage); yes (promotion) |

Problems found and fixed in the prompts during the run:

- `create_pull_request` from an automation always opens a **draft**, even with `draft:false`.
  The implementer and the shepherd now call `update_pull_request_draft_state`.
- A PR created seconds earlier may not resolve yet ("Could not resolve to an Issue"). The
  implementer retries labelling, and PR #9 lost its labels and `Closes #4` the first time.
- `pull_request_merged` and `issue_closed` both fire on a merge, which duplicated dispatcher
  comments. The dispatcher now listens to `issue_closed` only.
- Implementers sometimes omit `Closes #n` (PR #11), which left #6 open but labelled `sf:done`
  and held back #7. The shepherd now adds `Closes #n` before merging and closes the task if it's
  still open. The dispatcher closes any open task labelled `sf:done`.
- The dispatcher ran 4 s after #12 was opened and missed it, probably because issue search lags.
  It now lists issues with `list_issues` and reads the triggering issue directly.

Gaps that remain in v2:

- **Held CI** (the one human step). There's no automation tool that approves `action_required`
  runs. Options: a gh-aw `approve-workflow-run` safe output, or relaxing the repo's Actions
  approval setting for the agent. PR #14 (the last BRD task) had a clean review but waited about
  80 minutes on held CI. The shepherd asked for approval in a PR comment, but a personal
  automation acts as the user, so that comment notified nobody. The shepherd now also labels the
  PR `sf:held-ci` (cleared once runs are released) and the reporter lists it first under "Needs a
  human"; still no push notification. After release, BRD #1 got `sf:delivered`: all 5 BRD tasks
  merged.
- **No trigger on CI success.** `workflow_run` fires on failure only, so after a person
  releases CI and it passes, the shepherd waits for its hourly sweep or a manual run (PR #10).
- **Stale task state.** The first #5 implementer task still reports `in_progress` long after
  its session pushed, so task state is not a reliable "done" signal. The factory reads the
  labels instead.
- **Public repos disable cloud automations.** Making sf-gh-tier public set
  `automations_enabled:false` and the automations API returned 404. Making it private again
  restored them with their configuration intact. A public demo needs a private factory repo.
- **Personal automations can't approve their own PRs**, so reviews are COMMENT plus a verdict
  marker and the shepherd enforces it. That's prompt enforcement, not a branch-protection gate.

## v1 live run evidence

Sandbox: [andrejpk/sf-automation-sandbox](https://github.com/andrejpk/sf-automation-sandbox)
(private, GitHub Free, personal automations acting as `andrejpk`). BRD: a three-task Python CLI
(`tally`). Task #2 merged; #3 is blocked by finding 1; #4 waits on dependencies.

| Step | Original app | What happened here | Human needed? |
| --- | --- | --- | --- |
| Plan BRD into tasks | Foundry agent + `github_service` | `sf-planner` on label `sf:plan` created #2–#4 with acceptance criteria and dependencies (0.58 credits) | No |
| Assign Copilot (WIP limit) | REST assign, parallel limit 3 | `sf-dispatcher` picked the right task. `update_issue_assignees` rejected `Copilot` and `copilot-swe-agent` ("Issue.assignees (invalid)") and accepted `copilot-swe-agent[bot]`. Then Copilot posted *"unable to start working on this issue: This may be caused by a repository ruleset violation"*. The repo has no rulesets. Reproduced on #3 right after the merge | **Yes**: unassign and reassign with `gh issue edit --add-assignee @copilot` |
| Detect session finished | Poll the session API | `copilot_work_finished` is not an automation trigger. The hourly sweep or a manual run picks it up | Latency only |
| Mark draft ready | REST | `update_pull_request_draft_state` worked. The `ready_for_review` event it causes re-triggers the shepherd, so chaining works | No |
| Release held CI runs | Re-run endpoint | Copilot PR runs show `action_required`. The approve API returns 403 ("not from a fork PR"). The automation's `retry_workflow_run` refuses them ("must be completed with a failure conclusion"). `gh run rerun` as a user works | **Yes** |
| Request Copilot code review | `POST /pulls/{n}/copilot-code-review` | `request_pull_request_reviewers` with `copilot-pull-request-reviewer` or `Copilot` reports success but creates no request. The REST call as a user works | **Yes** (or enable automatic Copilot review, which needs rulesets; see below) |
| React to Copilot review | Poller | `pull_request_review_submitted` did **not** fire for `copilot-pull-request-reviewer[bot]` reviews, even with "Can be triggered by: People and Copilot". This happened twice | Latency (hourly sweep) |
| Route findings back | PR-level `@copilot` comment | The shepherd wrote a correct comment with the `sf:remediation n=1` marker. Copilot ignored it. A human-authored copy started a session at once, and Copilot fixed the test and merged `main` | **Yes** |
| Wake on Copilot push | Poller | The shepherd had no `synchronize` trigger, so it was added during the run | No (after fix) |
| Merge with gates | `gates.py`, expected head SHA | The shepherd checked the Copilot review of head `7cdf25f` (no findings), CI and mergeability. It posted `sf:merge-evidence` and squash-merged with the head SHA | No |
| Status report | Dashboard | `sf-status-reporter` keeps the `sf:status` issue current ([#7](https://github.com/andrejpk/sf-automation-sandbox/issues/7)): a task table plus a "Needs a human" list | No |

Cost of the automations in the live run: about **7.9 AI credits over 15 runs** (planner 0.6,
dispatcher 4.4 over 6 runs, shepherd 2.9 over 8 runs). Copilot cloud agent and code review
sessions bill separately.

Other findings:

* **PR authorship.** PRs that Copilot opens are authored by the *assigning user*, with Copilot as
  assignee. A prompt that scopes on "authored by Copilot" misses them. The shepherd now matches a
  Copilot assignee or a `copilot/` branch.
* **Trigger limits.** `workflow_run` triggers accept only `failure` conclusions (422 otherwise),
  so "CI went green" can't trigger the shepherd directly.
* **Over-cautious blocking.** One shepherd run blocked a PR because an *optional* label check
  failed. Prompt rules need explicit "optional, never block" wording, where code would simply skip
  the check. Issue #2 was left labeled `sf:blocked` after it merged. Label hygiene depends on the
  model noticing.
* **Rulesets.** The rulesets API returns 403 on a private repository on GitHub Free. Required
  checks, required reviews and automatic Copilot review on push are unavailable there, so every
  gate is prompt-only on that plan.
* **Credit limits.** `run_limit` and `usage_limits` work, but they aren't in the published REST
  reference. The API stores them in nano-credits, with a minimum of 30 credits per run.
* **Transcripts.** Automation run transcripts are only viewable through
  `gh agent-task view <session-id> --log` (OAuth token, not a PAT) or the Agents tab, and the
  task id doesn't work as a lookup key there.

## Enforcement moves from code to prompt

| Gate (SPEC.md) | Original | Here |
| --- | --- | --- |
| Merge only when the latest Copilot review of the head has no findings | `gates.py` | Shepherd prompt rule plus the `sf:merge-evidence` comment. With rulesets (paid plans or public repos), "require Copilot review" and required checks can back it |
| Merge with the expected head SHA | Code | Prompt rule; `merge_pull_request` accepts the SHA, and it was used in the live run |
| Checks pass | Code | Prompt rule; a ruleset "required status checks" where available |
| Approval exists | Code (recorded as a comment because the assigner can't approve their own Copilot PR) | Not enforced on Free. Shared automations act as Copilot, so their PRs need one extra human approval if approvals are required |
| Remediation cap 3, then block | Counter in code | Hidden `sf:remediation n=` markers counted by the model |
| WIP limit and dependency order | Code | Dispatcher prompt rule. The model counts `sf:in-progress` issues and parses `## Dependencies` |
| Idempotency | Database and service state | "Check before you act" prompt rule; GitHub is the only memory |

A model can miscount, misread a marker, or (as seen) block when it shouldn't. Treat the prompt
gates as advisory unless a ruleset backs them.

## UI story

The original app is a single local web UI: BRD chat with the lead engineer, a configuration
screen, a Projects v2 board it maintains, and a live view of each task's PR, review cycle and gate
state. In this port, that experience is spread across GitHub surfaces:

| Need | Where it lives now | Quality |
| --- | --- | --- |
| BRD drafting and refinement chat | Copilot app or VS Code chat with hve-core's `brd-builder` agent (linked by APM). The result is committed as `docs/BRD.md` and the `sf:brd` issue | Good for one author. No shared, structured BRD editor |
| Kick off planning | Add the `sf:plan` label | Works, but you have to know the label |
| Backlog and status board | Issue list filtered by `sf:*` labels, sub-issues on the BRD issue, the `sf:status` issue | Usable. **No Projects v2 board**, because automations have no Projects v2 tool. gh-aw's `update-project` could add one |
| What the automations did | Repo **Agents** tab: automation runs and session logs; `gh agent-task list` | Per run only. No pipeline view; you can't see why a run did nothing without opening its log |
| Copilot coding progress | PR timeline and session log in the Agents tab | Good per PR |
| Review findings and remediation count | PR review threads plus hidden markers | Markers are invisible in the UI by design. Nothing shows "cycle 2 of 3" |
| Gate state ("why isn't this merging?") | Read the PR: checks, reviews, the `sf:merge-evidence` comment | No single gate panel |
| **Human actions the loop needs** (reassign Copilot, re-run held CI, request Copilot review, re-post `@copilot`) | Scattered: issue sidebar, Actions tab, PR reviewers menu, PR comment | **No home.** Nothing tells you an action is waiting except `sf:blocked` comments and `sf:held-runs` comments |
| Spend | Automation run details (nano-credits via API); billing settings | No per-feature or per-BRD roll-up |
| Configuration (WIP, cycle cap, model) | Constants in `_conventions.md`, re-installed with `install.ps1` | No UI. Automations live outside Git; this repo keeps the definitions as code |
| Copilot app Projects | Can host the BRD conversation and the `orchestrate` skill from andrejpk/andrej-agent-kit, which is linked by APM | Personal. Not shared with a customer or team |

What a **customer** sees: issues and PRs in a private repository they must have access to, and
the status issue. What a **team member** sees: the same, plus the Agents tab. Neither gets a
mission-control view or a queue of "things only a human can do".

A GitHub-only Mission Control prototype is built (no PR yet). It's a no-build static SPA
that calls the GitHub API with the viewer's own token, showing an attention queue, pipeline, task
DAG, PR gates, automations and credits, with no added compute, storage or model. Every write
re-reads first and refuses if anything changed. It's on the
`andrejky-microsoft-factory-mission-control-design` branch (1a270c5) in
`automations/mission-control/`, aligned with the v2 label-driven design: the human actions it
offers are label writes and releasing held CI. Read-only live testing against sf-gh-tier found:
* The automations (`/agents`) API rejects browser CORS, so a localhost relay restricted to an
  allowlist of paths is needed. On GitHub Pages the automations panel is unavailable.
* The OAuth device flow can't run in a browser, so users paste a token.
* Live writes are still untested.

## Other things this approach loses or changes

* **Identity and billing.** Personal automations act as and bill you. Shared automations act as
  Copilot and bill the repository owner. The Foundry model choice and Azure billing disappear.
* **Public repositories.** Cloud automations run only in private or internal repositories. A
  public fork can hold the code, but not run the loop.
* **Latency.** Several transitions wait for the hourly sweep: session finished, Copilot review
  submitted, CI succeeded. The original poller ran every 60 seconds.
* **State.** All state is labels, markers and issue bodies. That's resilient, but there's no
  history store or analytics beyond what GitHub keeps.
* **Definitions outside Git.** Automations aren't versioned by GitHub. `install.ps1` and
  `definitions/` provide that, but someone can still edit an automation in the UI and drift.
* **Preview APIs.** The automations API version is `2026-03-10` (public preview). Trigger names,
  tool names and limits may change.

## Reuse from microsoft/hve-core and andrej-agent-kit

Linked through APM and `gh aw add` with pinned commits (see [README.md](README.md#provenance-and-updates)):

* **Used:** `untrusted-content-boundary` (every prompt), `backlog-management` and `backlog-plan`
  (planner), `code-review` (via gh-aw `pr-review`), the `brd-builder` agent, the gh-aw
  `pr-review` workflow (`/review` → `needs-revision`/`review-passed`, which the shepherd reads),
  and andrej-agent-kit `gh-orchestrator` skills `orchestrate` and `issue-intake`.
* **Overlaps, not used:**
  * hve-core `issue-implement` runs the Copilot engine in Actions. We use Copilot cloud agent so
    the original Copilot PR experience is preserved.
  * `issue-triage`'s `agent-ready` label is replaced by `sf:ready` from the dispatcher, which also
    enforces WIP and dependency order.
  * The `backlog-groom` orchestrator pattern overlaps the reporter and dispatcher sweeps.
  * The dispatcher and shepherd are ours, because hve-core has no WIP-limited dispatcher or
    remediation loop with a cycle cap.
* **APM quirks:**
  * APM installs skills and `.agent.md` agents, but not canvases or extensions.
  * Lockfile content hashes differ between Windows and Linux, so generate the lock on Linux.
  * apm-cli 0.35.1 on Windows didn't deploy upstream LICENSE files; 0.36.1 on Linux did.
  * hve-core's `pr-review.md` hard-codes `.github/skills/...`, so it needs a local edit that
    `gh aw update` merges.
  * Dependabot and Renovate don't understand `apm.yml`, so a scheduled workflow with a PAT
    (`SF_DEPS_TOKEN`) opens the update PRs.

## What would close the gaps

* Copilot sessions should start when an automation assigns Copilot, and should honor `@copilot`
  comments that automations post, at least for automations a maintainer owns.
* `request_pull_request_reviewers` should support the Copilot reviewer, or a tool should expose
  `copilot-code-review`.
* Add triggers for `copilot_work_finished`, successful `workflow_run`, and Copilot review
  submissions.
* Expose a tool to approve or re-run held workflow runs for Copilot PRs.
* Add a Projects v2 item tool.
* Until then, a gh-aw workflow using a fine-grained PAT (`assign-to-agent`, `add-reviewer`,
  `approve-workflow-run`, `update-project`) can take over the human steps, at the cost of a
  stored token.
