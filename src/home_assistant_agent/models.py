from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class EntitySnapshot:
    entity_id: str
    domain: str
    state: str | None
    friendly_name: str | None = None
    area_id: str | None = None
    device_id: str | None = None
    label_ids: list[str] = field(default_factory=list)
    disabled_by: str | None = None
    hidden_by: str | None = None
    icon: str | None = None
    platform: str | None = None
    original_name: str | None = None
    registry_name: str | None = None
    has_live_state: bool = True
    last_changed: str | None = None
    last_updated: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AutomationSummary:
    entity_id: str
    name: str
    state: str | None
    last_triggered: str | None
    mode: str | None
    current_runs: int | None
    area_id: str | None = None
    is_enabled: bool = True
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Issue:
    issue_id: str
    category: str
    severity: str
    title: str
    details: str
    affected_ids: list[str] = field(default_factory=list)
    suggestion: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ChangeAction:
    action_id: str
    category: str
    description: str
    action_type: str
    target_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    destructive: bool = False
    supported: bool = True
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ChangePlan:
    plan_id: str
    kind: str
    summary: str
    actions: list[ChangeAction]
    notes: list[str] = field(default_factory=list)
    requires_confirmation: bool = True
    approval_code: str | None = None
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "kind": self.kind,
            "summary": self.summary,
            "actions": [action.to_dict() for action in self.actions],
            "notes": self.notes,
            "requires_confirmation": self.requires_confirmation,
            "approval_code": self.approval_code,
            "created_at": self.created_at,
        }


@dataclass(slots=True)
class InventorySnapshot:
    generated_at: str
    home_assistant_config: dict[str, Any]
    services: list[dict[str, Any]]
    entities: list[EntitySnapshot]
    automations: list[AutomationSummary]
    devices: list[dict[str, Any]]
    areas: list[dict[str, Any]]
    labels: list[dict[str, Any]]
    integrations: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "home_assistant_config": self.home_assistant_config,
            "services": self.services,
            "entities": [entity.to_dict() for entity in self.entities],
            "automations": [automation.to_dict() for automation in self.automations],
            "devices": self.devices,
            "areas": self.areas,
            "labels": self.labels,
            "integrations": self.integrations,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class ApplyResult:
    plan_id: str
    applied_actions: list[dict[str, Any]]
    skipped_actions: list[dict[str, Any]]
    approval_verified: bool
    completed_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def new_issue_id(category: str, target: str) -> str:
    return f"{category}:{target}"


def new_plan_id(kind: str) -> str:
    return f"{kind}-{uuid4().hex[:12]}"


def new_action_id(prefix: str, target: str) -> str:
    safe_target = target.replace(".", "_").replace(":", "_")
    return f"{prefix}-{safe_target}"
