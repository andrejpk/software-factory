from software_factory import gates
from software_factory.github import CheckSummary

HEAD = "abc1234"


def pr(**over):
    base = {"head": {"sha": HEAD}, "base": {"ref": "main"}, "draft": False, "mergeable": True,
            "mergeable_state": "clean"}
    return {**base, **over}


def review(state="COMMENTED", commit=HEAD, at="2026-01-01T00:00:00Z"):
    return {"id": 1, "state": state, "commit_id": commit, "submitted_at": at, "body": ""}


def passed():
    return CheckSummary(total=1, passed=["ci"])


def test_clean_review_and_passing_checks_merges_through_lead_agent():
    d = gates.evaluate(pr(), review(), [], passed(), 0, no_checks_ok=False)
    assert d.action == "merge" and d.approval_path == "lead_agent"


def test_copilot_approval_is_preferred_path():
    d = gates.evaluate(pr(), review("APPROVED"), [], passed(), 0, no_checks_ok=False)
    assert d.action == "merge" and d.approval_path == "copilot"


def test_review_of_older_commit_does_not_count():
    reviews = [review(commit="old")]
    assert gates.latest_review_for_head(reviews, HEAD) is None
    d = gates.evaluate(pr(), None, [], passed(), 0, no_checks_ok=False)
    assert d.action == "wait"


def test_findings_trigger_remediation_until_limit_then_block():
    comments = [{"path": "index.html", "line": 3, "body": "Banner text is wrong"}]
    d = gates.evaluate(pr(), review(), comments, passed(), 0, no_checks_ok=False)
    assert d.action == "remediate" and "index.html:3" in d.findings[0]
    d = gates.evaluate(pr(), review(), comments, passed(), gates.MAX_REMEDIATION_CYCLES, no_checks_ok=False)
    assert d.action == "block"


def test_pending_or_failed_checks_prevent_merge():
    pending = CheckSummary(total=1, pending=["ci"])
    assert gates.evaluate(pr(), review(), [], pending, 0, no_checks_ok=False).action == "wait"
    failed = CheckSummary(total=1, failed=["ci (failure)"])
    assert gates.evaluate(pr(), review(), [], failed, 0, no_checks_ok=False).action == "remediate"


def test_workflow_runs_awaiting_approval_prevent_merge():
    held = CheckSummary(total=2, passed=["copilot-pull-request-reviewer"], awaiting_approval=["Test"])
    d = gates.evaluate(pr(), review(), [], held, 0, no_checks_ok=True)
    assert d.action == "wait" and "held workflow runs" in d.reason


def test_missing_checks_wait_unless_repository_has_no_workflows():
    none = CheckSummary()
    assert gates.evaluate(pr(), review(), [], none, 0, no_checks_ok=False).action == "wait"
    assert gates.evaluate(pr(), review(), [], none, 0, no_checks_ok=True).action == "merge"


def test_merge_conflict_is_routed_to_copilot():
    d = gates.evaluate(pr(mergeable=False, mergeable_state="dirty"), review(), [], passed(), 0, no_checks_ok=False)
    assert d.action == "remediate" and any("merge conflicts" in f for f in d.findings)


def test_draft_or_unknown_mergeability_waits():
    assert gates.evaluate(pr(draft=True), review(), [], passed(), 0, no_checks_ok=False).action == "wait"
    assert gates.evaluate(pr(mergeable=None), review(), [], passed(), 0, no_checks_ok=False).action == "wait"
