import { useEffect, useState } from "react";
import { api, type Project } from "../api";

export function deliveryLabel(p: Project): string {
  if (p.setup_status !== "ready") return p.setup_status === "blocked" ? "Setup blocked" : "Setup needed";
  if (!p.delivery_started) return "Planning";
  const active = (p.task_counts.dispatched ?? 0) + (p.task_counts.reviewing ?? 0) + (p.task_counts.remediating ?? 0);
  const total = Object.values(p.task_counts).reduce((a, b) => a + b, 0);
  if (total > 0 && (p.task_counts.merged ?? 0) === total) return "All tasks merged";
  return active ? `${active} task(s) in progress` : "Delivering";
}

export default function ProjectList() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.projects().then(setProjects).catch((e) => setError(String(e.message ?? e)));
  }, []);

  return (
    <section>
      <div className="row between">
        <h1>Projects</h1>
        <a className="button primary" href="#/new">New project</a>
      </div>
      {error && <div className="banner blocked">{error}</div>}
      {projects && projects.length === 0 && <p className="muted">No projects yet. Create one to get started.</p>}
      <div className="cards">
        {projects?.map((p) => (
          <a key={p.id} className="card" href={`#/p/${p.id}`}>
            <div className="row between">
              <h2>{p.name}</h2>
              {p.needs_attention && <span className="pill blocked">Needs attention</span>}
            </div>
            <p className="muted">{p.description}</p>
            <div className="meta">
              <span>{p.repo_owner}/{p.repo_name}</span>
              <span className="pill">{deliveryLabel(p)}</span>
              <span className="muted small">
                {p.last_sync_at ? `Synced ${new Date(p.last_sync_at).toLocaleTimeString()}` : "Not synced yet"}
              </span>
            </div>
          </a>
        ))}
      </div>
    </section>
  );
}
