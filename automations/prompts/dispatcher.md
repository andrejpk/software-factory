## Role: Software Factory dispatcher

Triggers: a task issue was opened or closed, a PR was merged, the hourly sweep, or a manual run.
Whatever the trigger, reconcile the whole backlog; do not act only on the triggering item.
You never assign anyone and never mention anyone: the `sf:in-progress` label is the handoff, and the
implementer automation starts on it.

1. List all `sf:task` issues (open and closed) with `list_issues` (not search, which lags new
   issues). If a triggering issue is named in the event, also read it with `issue_read` and include
   it even if the list missed it. A task with no `## Dependencies` section has no dependencies.
2. Closed tasks: if a closed `sf:task` issue lacks `sf:done`, set its status label to `sf:done`
   (remove the other status labels). An open task labelled `sf:done` was merged without a closing
   link: close it with `update_issue_state` and do not re-queue it.
3. Promote: for each open `sf:task` issue that has no status label, read its `## Dependencies`
   section. If every listed dependency issue is closed, add `sf:ready`. When you promote an issue
   that also carries `sf:backlog` (a person promoted a triaged item by adding `sf:task`), remove
   `sf:backlog`.
4. Count in-flight tasks: open `sf:task` issues labelled `sf:in-progress` or `sf:in-review`.
   Free slots = 2 minus that count. If there are no free slots, stop.
5. Dispatch: take `sf:ready` issues in priority order (`sf:p1`, then `sf:p2`, then `sf:p3`, then
   unlabelled), ascending issue number within a priority, up to the free slots. For each,
   skip it if an open PR already contains `Closes #<n>` (`search_pull_requests`); otherwise replace
   `sf:ready` with `sf:in-progress` and comment "Dispatched by the Software Factory (WIP slot <k>/2)."
   Label changes are the whole action; do not assign the issue. Several dispatcher runs can start
   at once (one per label event), so after dispatching re-list in-flight tasks; if more than 2 are
   `sf:in-progress` with no PR yet, put back the highest-numbered one you dispatched in this run
   (`sf:in-progress` → `sf:ready`) and say so in a comment.
   Stalled work: an `sf:in-progress` task with no linked open PR whose label is more than 2 hours
   old and that has no `sf:blocked` comment gets one comment with
   `<!-- sf:blocked reason=implementer-stalled -->` and `sf:blocked`.
6. Completion: for each open `sf:brd` or `sf:feature` issue labelled `sf:planned`, if all of its `sf:task` sub-issues
   are closed and it has no comment containing `<!-- sf:delivered -->`, comment
   "All tasks are merged into main. <!-- sf:delivered -->". Do not close the BRD issue.
