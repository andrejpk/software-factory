## Role: Software Factory status reporter

Triggers: something needs a human (`sf:blocked`, `sf:needs-design` or `sf:held-ci` added), a
task closed, or a manual run. You replace the original app's backlog view with one issue.

1. Find the open issue labelled `sf:status`. If none exists, create one titled
   "Software Factory status" with label `sf:status`.
2. Gather: every `sf:brd` issue; every `sf:task` issue with its status label, assignees and linked PR;
   each open Copilot PR with draft state, latest Copilot review state for its head, workflow-run
   conclusions and the number of `<!-- sf:remediation` markers.
3. Replace the status issue body with:
   * A one-line headline (for example "3 of 5 tasks merged, 1 in review, 1 blocked").
   * A table: Task | Status | PR | Review | Checks | Fix cycles.
   * A "Needs a human" list, placed first, of every `sf:blocked` item with the reason from its
     block comment, and every PR labelled `sf:held-ci` or with workflow runs waiting for approval
     (say how long it has waited and that a maintainer must approve or re-run the CI).
   * "Last updated <UTC timestamp>".
   Write it for a non-technical customer: plain language, no diffs, no code.
4. Do not change any other issue or PR.
