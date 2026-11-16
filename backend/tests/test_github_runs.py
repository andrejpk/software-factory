import httpx

from software_factory.github import API, GitHub

SHA = "a80f135"


def client_for(runs: list[dict], jobs_by_run: dict[int, int], calls: list[str]) -> GitHub:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append(f"{request.method} {path}")
        if path.endswith(f"/commits/{SHA}/check-runs"):
            return httpx.Response(200, json={"check_runs": [
                {"name": "copilot-pull-request-reviewer", "status": "completed", "conclusion": "success"}]})
        if path.endswith(f"/commits/{SHA}/status"):
            return httpx.Response(200, json={"statuses": []})
        if path.endswith("/actions/runs") and request.method == "GET":
            return httpx.Response(200, json={"workflow_runs": runs})
        if "/jobs" in path:
            run_id = int(path.split("/runs/")[1].split("/")[0])
            return httpx.Response(200, json={"total_count": jobs_by_run.get(run_id, 0), "jobs": []})
        return httpx.Response(201, json={})

    return GitHub("t", "me", "repo", client=httpx.Client(base_url=API, transport=httpx.MockTransport(handler)))


def run(rid, status="completed", conclusion="failure", attempt=1, event="pull_request"):
    return {"id": rid, "name": "Test", "event": event, "status": status, "conclusion": conclusion,
            "run_attempt": attempt}


def test_run_that_never_started_is_held_and_gets_rerun():
    calls: list[str] = []
    gh = client_for([run(1), run(2, event="dynamic", conclusion="success")], {}, calls)
    summary = gh.check_summary(SHA)
    assert summary.awaiting_approval == ["Test"] and not summary.all_passed
    started, stuck = gh.start_held_runs(SHA)
    assert (started, stuck) == (1, []) and "POST /repos/me/repo/actions/runs/1/rerun" in calls


def test_run_that_executed_jobs_is_not_held():
    gh = client_for([run(1)], {1: 1}, [])
    assert gh.check_summary(SHA).awaiting_approval == []


def test_run_that_never_starts_after_retries_counts_as_failed():
    gh = client_for([run(1, attempt=3)], {}, [])
    summary = gh.check_summary(SHA)
    assert summary.awaiting_approval == [] and summary.failed == ["Test (workflow failed to start)"]
