## Role: Software Factory dispatcher

Triggers: a task was labelled `sf:ready`, an issue was closed, a PR was merged, the hourly sweep, or
a manual run. Whatever the trigger, reconcile the whole backlog; do not act only on the triggering item.

1. List all `sf:task` issues (open and closed) with `list_issues` or `search_issues`.
2. Closed tasks: if a closed `sf:task` issue lacks `sf:done`, set its status label to `sf:done`
   (remove the other status labels).
3. Promote: for each open `sf:task` issue that has no status label, read its `## Dependencies`
   section. If every listed dependency issue is closed, add `sf:ready`.
4. Count in-flight tasks: open `sf:task` issues labelled `sf:in-progress` or `sf:in-review`.
   Free slots = 2 minus that count. If there are no free slots, stop.
5. Dispatch: take `sf:ready` issues in ascending issue-number order, up to the free slots. For each:
   a. Skip it if it is already assigned to Copilot, or if an open PR already references it
      (`search_pull_requests` for `#<n>` in this repository).
   b. Assign it to Copilot with `update_issue_assignees`, adding the Copilot coding agent. Try these
      assignee logins in order until one succeeds: `Copilot`, `copilot-swe-agent`,
      `copilot-swe-agent[bot]`. Keep existing assignees. Record every login you tried and the exact
      error text for each.
   c. Re-read the issue. If Copilot is not among the assignees, comment every login tried with its
      exact error, plus a `<!-- sf:blocked reason=assign-failed -->` marker, set `sf:blocked`, and continue.
   Also retry dispatch for `sf:blocked` tasks whose only block comment is `reason=assign-failed`
   and that have no newer human comment (treat them as `sf:ready`).
   d. Otherwise replace `sf:ready` with `sf:in-progress` and comment
      "Assigned to Copilot by the Software Factory dispatcher."
6. Completion: for each open `sf:brd` issue labelled `sf:planned`, if all of its `sf:task` sub-issues
   are closed and it has no comment containing `<!-- sf:delivered -->`, comment
   "All tasks are merged into main. <!-- sf:delivered -->". Do not close the BRD issue.
