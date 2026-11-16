"""Pure decision logic for the review and merge loop, kept free of I/O so it can be unit tested."""

from dataclasses import dataclass, field

from .github import CheckSummary

MAX_REMEDIATION_CYCLES = 3


@dataclass
class Decision:
    action: str  # wait | remediate | merge | block
    reason: str = ""
    findings: list[str] = field(default_factory=list)
    approval_path: str = ""  # copilot | lead_agent


def latest_review_for_head(reviews: list[dict], head_sha: str) -> dict | None:
    """Latest completed Copilot review whose commit matches the current head."""
    done = [r for r in reviews if r.get("commit_id") == head_sha
            and r.get("state") in ("COMMENTED", "APPROVED", "CHANGES_REQUESTED")]
    done.sort(key=lambda r: r.get("submitted_at") or "")
    return done[-1] if done else None


def format_finding(c: dict) -> str:
    where = c.get("path") or "general"
    line = c.get("line") or c.get("original_line")
    loc = f"{where}:{line}" if line else where
    body = " ".join((c.get("body") or "").split())
    if len(body) > 600:
        body = body[:600] + "..."
    return f"`{loc}`: {body}"


def evaluate(pr: dict, review: dict | None, review_comments: list[dict], checks: CheckSummary,
             remediation_count: int, *, no_checks_ok: bool) -> Decision:
    """Decide the next step for a PR whose Copilot coding session has finished."""
    head = pr["head"]["sha"]
    if pr.get("base", {}).get("ref") != "main":
        return Decision("block", f"PR targets {pr.get('base', {}).get('ref')} instead of main")
    if review is None:
        return Decision("wait", "Waiting for Copilot review of the current head")
    if review.get("commit_id") != head:
        return Decision("wait", "Latest Copilot review is for an older commit")
    if checks.awaiting_approval:
        return Decision("wait", "Waiting for held workflow runs to start: " + ", ".join(checks.awaiting_approval))
    if checks.pending:
        return Decision("wait", "Waiting for checks: " + ", ".join(checks.pending))

    findings = [format_finding(c) for c in review_comments]
    if review.get("state") == "CHANGES_REQUESTED" and not findings:
        findings.append(" ".join((review.get("body") or "Copilot requested changes.").split()))
    findings += [f"Failed check: {f}" for f in checks.failed]
    conflict = pr.get("mergeable") is False and pr.get("mergeable_state") == "dirty"
    if conflict:
        findings.append("This PR has merge conflicts with main. Merge main into the branch and resolve them.")

    if findings:
        if remediation_count >= MAX_REMEDIATION_CYCLES:
            return Decision("block", f"Remediation limit of {MAX_REMEDIATION_CYCLES} cycles reached", findings)
        return Decision("remediate", "Copilot review or checks reported issues", findings)

    if checks.total == 0 and not no_checks_ok:
        return Decision("wait", "Waiting for checks to start")
    if pr.get("draft"):
        return Decision("wait", "PR is still a draft")
    if pr.get("mergeable") is None:
        return Decision("wait", "GitHub is still computing mergeability")
    if pr.get("mergeable") is False:
        return Decision("wait", f"PR is not mergeable yet ({pr.get('mergeable_state')})")

    path = "copilot" if review.get("state") == "APPROVED" else "lead_agent"
    return Decision("merge", "Copilot review of the current head found no issues", approval_path=path)
