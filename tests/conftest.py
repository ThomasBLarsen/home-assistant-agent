from __future__ import annotations

from pathlib import Path

import pytest

from home_assistant_agent.config import Settings


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    logs_dir = tmp_path / "logs"
    change_plan_dir = logs_dir / "change_plans"
    logs_dir.mkdir(parents=True, exist_ok=True)
    change_plan_dir.mkdir(parents=True, exist_ok=True)
    return Settings(
        home_assistant_url="http://example.local:8123",
        home_assistant_token="test-token",
        approval_secret="approval-secret",
        allowed_service_domains={"automation", "homeassistant", "scene", "script"},
        request_timeout_seconds=5,
        websocket_timeout_seconds=5,
        workspace_dir=tmp_path,
        logs_dir=logs_dir,
        change_plan_dir=change_plan_dir,
        audit_log_path=logs_dir / "audit.jsonl",
    )
