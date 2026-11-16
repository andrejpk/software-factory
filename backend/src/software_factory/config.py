import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _load_env() -> None:
    # Process environment wins; then working-directory .env; then the data-directory .env.
    load_dotenv(Path.cwd() / ".env", override=False)
    repo_env = Path(__file__).resolve().parents[3] / ".env"
    load_dotenv(repo_env, override=False)
    load_dotenv(default_home() / ".env", override=False)


def default_home() -> Path:
    override = os.environ.get("SOFTWARE_FACTORY_HOME", "").strip()
    if override:
        return Path(override)
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "SoftwareFactory"


@dataclass(frozen=True)
class Settings:
    project_endpoint: str
    model_deployment: str
    tenant_id: str
    agent_name: str
    home: Path
    log_level: str
    poll_seconds: int
    host: str
    port: int

    @property
    def foundry_configured(self) -> bool:
        return bool(self.project_endpoint and self.model_deployment)


def load_settings() -> Settings:
    _load_env()
    home = default_home()
    return Settings(
        project_endpoint=os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "").strip(),
        model_deployment=os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "").strip(),
        tenant_id=os.environ.get("AZURE_TENANT_ID", "").strip(),
        agent_name=os.environ.get("SOFTWARE_FACTORY_AGENT_NAME", "").strip() or "software-factory-lead",
        home=home,
        log_level=os.environ.get("LOG_LEVEL", "INFO").strip() or "INFO",
        poll_seconds=int(os.environ.get("SOFTWARE_FACTORY_POLL_SECONDS", "60")),
        host="127.0.0.1",
        port=int(os.environ.get("SOFTWARE_FACTORY_PORT", "8765")),
    )
