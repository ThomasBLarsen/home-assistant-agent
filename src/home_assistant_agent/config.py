from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ALLOWED_SERVICE_DOMAINS = {
    "automation",
    "homeassistant",
    "scene",
    "script",
}


def _parse_dotenv_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        values[key] = value
    return values


def _comma_separated_set(value: str | None) -> set[str]:
    if not value:
        return set(DEFAULT_ALLOWED_SERVICE_DOMAINS)
    return {item.strip() for item in value.split(",") if item.strip()}


@dataclass(slots=True)
class Settings:
    home_assistant_url: str
    home_assistant_token: str
    approval_secret: str
    allowed_service_domains: set[str]
    request_timeout_seconds: float
    websocket_timeout_seconds: float
    workspace_dir: Path
    logs_dir: Path
    change_plan_dir: Path
    audit_log_path: Path

    @property
    def api_base_url(self) -> str:
        return f"{self.home_assistant_url.rstrip('/')}/api"


def load_settings(env_file: str | Path | None = None) -> Settings:
    workspace_dir = Path.cwd()
    dotenv_path = Path(env_file) if env_file else workspace_dir / ".env"
    file_values = _parse_dotenv_file(dotenv_path)

    def read(name: str, default: str | None = None) -> str | None:
        return os.getenv(name, file_values.get(name, default))

    home_assistant_url = read("HOME_ASSISTANT_URL")
    home_assistant_token = read("HOME_ASSISTANT_TOKEN")
    if not home_assistant_url:
        raise ValueError("HOME_ASSISTANT_URL is required.")
    if not home_assistant_token:
        raise ValueError("HOME_ASSISTANT_TOKEN is required.")

    logs_dir = workspace_dir / "logs"
    change_plan_dir = logs_dir / "change_plans"
    audit_log_path = logs_dir / "audit.jsonl"

    settings = Settings(
        home_assistant_url=home_assistant_url.rstrip("/"),
        home_assistant_token=home_assistant_token,
        approval_secret=read("HA_AGENT_APPROVAL_SECRET", home_assistant_token) or home_assistant_token,
        allowed_service_domains=_comma_separated_set(read("HA_AGENT_ALLOWED_SERVICE_DOMAINS")),
        request_timeout_seconds=float(read("HA_AGENT_REQUEST_TIMEOUT", "20") or "20"),
        websocket_timeout_seconds=float(read("HA_AGENT_WEBSOCKET_TIMEOUT", "20") or "20"),
        workspace_dir=workspace_dir,
        logs_dir=logs_dir,
        change_plan_dir=change_plan_dir,
        audit_log_path=audit_log_path,
    )
    ensure_runtime_directories(settings)
    return settings


def ensure_runtime_directories(settings: Settings) -> None:
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    settings.change_plan_dir.mkdir(parents=True, exist_ok=True)


def redact_secret(value: str, visible: int = 4) -> str:
    if len(value) <= visible * 2:
        return "*" * len(value)
    return f"{value[:visible]}...{value[-visible:]}"
