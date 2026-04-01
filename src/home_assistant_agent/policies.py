from __future__ import annotations

import hashlib

from .config import Settings
from .models import ChangeAction, ChangePlan


BLOCKED_ACTION_TYPES = {
    "delete_entity",
    "bulk_disable_entities",
    "replace_automation",
    "remove_integration",
}

SUPPORTED_ACTION_TYPES = {
    "disable_entity",
    "enable_automation",
}


class PolicyEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def attach_approval(self, plan: ChangePlan) -> ChangePlan:
        plan.approval_code = self.approval_code(plan.plan_id)
        plan.requires_confirmation = bool(plan.actions)
        return plan

    def approval_code(self, plan_id: str) -> str:
        digest = hashlib.sha256(f"{plan_id}:{self.settings.approval_secret}".encode("utf-8")).hexdigest()
        return digest[:12]

    def verify_approval(self, plan_id: str, approval_code: str | None) -> bool:
        if not approval_code:
            return False
        return approval_code == self.approval_code(plan_id)

    def can_call_service(self, domain: str) -> tuple[bool, str | None]:
        if domain not in self.settings.allowed_service_domains:
            return (
                False,
                f"Service domain '{domain}' is not in the allowlist: {sorted(self.settings.allowed_service_domains)}",
            )
        return True, None

    def evaluate_action(self, action: ChangeAction) -> ChangeAction:
        if action.action_type in BLOCKED_ACTION_TYPES:
            action.supported = False
            action.reason = "This action type is blocked by default policy."
            return action

        if action.action_type not in SUPPORTED_ACTION_TYPES:
            action.supported = False
            action.reason = action.reason or "This action requires manual review in guarded-write mode."
            return action

        if action.destructive:
            action.supported = False
            action.reason = "Destructive actions are blocked from auto-apply."
            return action

        return action

    def evaluate_plan(self, plan: ChangePlan) -> ChangePlan:
        plan.actions = [self.evaluate_action(action) for action in plan.actions]
        return self.attach_approval(plan)
