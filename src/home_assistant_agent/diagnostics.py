from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from .models import ChangeAction, ChangePlan, InventorySnapshot, Issue, new_action_id, new_issue_id, new_plan_id


UNHEALTHY_ENTITY_STATES = {"unknown", "unavailable"}
STALE_AUTOMATION_DAYS = 90


def find_issues(inventory: InventorySnapshot) -> list[Issue]:
    issues: list[Issue] = []
    name_groups: dict[str, list[str]] = defaultdict(list)

    for entity in inventory.entities:
        display_name = (entity.friendly_name or entity.registry_name or "").strip().lower()
        if display_name:
            name_groups[display_name].append(entity.entity_id)

        if entity.state in UNHEALTHY_ENTITY_STATES:
            issues.append(
                Issue(
                    issue_id=new_issue_id("entity_unhealthy", entity.entity_id),
                    category="entity_unhealthy",
                    severity="high",
                    title=f"{entity.entity_id} is reporting {entity.state}",
                    details="The entity is currently unavailable or unknown, which usually indicates an integration, device, or registry mismatch.",
                    affected_ids=[entity.entity_id],
                    suggestion="Review the backing integration or consider disabling unused entities after verification.",
                )
            )

        if not entity.has_live_state:
            issues.append(
                Issue(
                    issue_id=new_issue_id("entity_orphaned", entity.entity_id),
                    category="entity_orphaned",
                    severity="medium",
                    title=f"{entity.entity_id} is in the registry without a live state",
                    details="This often means the entity is stale, hidden, disabled, or tied to a removed integration.",
                    affected_ids=[entity.entity_id],
                    suggestion="Inspect the entity registry entry before keeping or disabling it.",
                )
            )

        if entity.disabled_by:
            issues.append(
                Issue(
                    issue_id=new_issue_id("entity_disabled", entity.entity_id),
                    category="entity_disabled",
                    severity="low",
                    title=f"{entity.entity_id} is disabled by {entity.disabled_by}",
                    details="Disabled entities are not necessarily a problem, but they are useful to include in cleanup reviews.",
                    affected_ids=[entity.entity_id],
                    suggestion="Remove it from cleanup candidates if it is intentionally disabled.",
                )
            )

    for name, entity_ids in name_groups.items():
        if len(entity_ids) > 1:
            issues.append(
                Issue(
                    issue_id=new_issue_id("duplicate_name", name),
                    category="duplicate_name",
                    severity="medium",
                    title=f"Duplicate entity name: {name}",
                    details="Multiple entities share the same display name, which can confuse dashboards, voice assistants, and AI tools.",
                    affected_ids=sorted(entity_ids),
                    suggestion="Review naming and disable stale duplicates where appropriate.",
                )
            )

    for automation in inventory.automations:
        if automation.state == "off":
            issues.append(
                Issue(
                    issue_id=new_issue_id("automation_disabled", automation.entity_id),
                    category="automation_disabled",
                    severity="medium",
                    title=f"{automation.entity_id} is disabled",
                    details="Disabled automations are often intentional, but they can also indicate drift after a broken edit or migration.",
                    affected_ids=[automation.entity_id],
                    suggestion="Re-enable if it should still be active.",
                )
            )

        last_triggered = _parse_iso_datetime(automation.last_triggered)
        if last_triggered and last_triggered < datetime.now(timezone.utc) - timedelta(days=STALE_AUTOMATION_DAYS):
            issues.append(
                Issue(
                    issue_id=new_issue_id("automation_stale", automation.entity_id),
                    category="automation_stale",
                    severity="low",
                    title=f"{automation.entity_id} has not triggered recently",
                    details=f"The automation has not triggered for at least {STALE_AUTOMATION_DAYS} days.",
                    affected_ids=[automation.entity_id],
                    suggestion="Review whether the trigger conditions still make sense.",
                    metadata={"last_triggered": automation.last_triggered},
                )
            )

    return sorted(issues, key=lambda issue: (issue.severity, issue.category, issue.issue_id))


def preview_entity_cleanup(inventory: InventorySnapshot) -> ChangePlan:
    actions: list[ChangeAction] = []
    notes: list[str] = []

    for entity in inventory.entities:
        if entity.disabled_by:
            continue

        if entity.state in UNHEALTHY_ENTITY_STATES:
            actions.append(
                ChangeAction(
                    action_id=new_action_id("disable_entity", entity.entity_id),
                    category="entity_cleanup",
                    description=f"Disable unhealthy entity {entity.entity_id}",
                    action_type="disable_entity",
                    target_id=entity.entity_id,
                    payload={"entity_id": entity.entity_id, "disabled": True},
                    destructive=False,
                )
            )

        elif not entity.has_live_state:
            actions.append(
                ChangeAction(
                    action_id=new_action_id("review_orphaned_entity", entity.entity_id),
                    category="entity_cleanup",
                    description=f"Review orphaned registry entry {entity.entity_id}",
                    action_type="review_entity",
                    target_id=entity.entity_id,
                    payload={"entity_id": entity.entity_id},
                    destructive=True,
                    supported=False,
                    reason="Registry-only cleanup still requires manual confirmation outside the safe apply path.",
                )
            )

    if not actions:
        notes.append("No obvious entity cleanup actions were detected from the current snapshot.")
    else:
        notes.append("Disabling unhealthy entities is the safest supported cleanup action in guarded-write mode.")

    return ChangePlan(
        plan_id=new_plan_id("entity-cleanup"),
        kind="entity_cleanup",
        summary=f"Prepared {len(actions)} entity cleanup actions.",
        actions=actions,
        notes=notes,
    )


def preview_automation_cleanup(inventory: InventorySnapshot) -> ChangePlan:
    actions: list[ChangeAction] = []
    notes: list[str] = []

    name_groups: dict[str, list[str]] = defaultdict(list)
    for automation in inventory.automations:
        name_groups[automation.name.strip().lower()].append(automation.entity_id)
        if automation.state == "off":
            actions.append(
                ChangeAction(
                    action_id=new_action_id("enable_automation", automation.entity_id),
                    category="automation_cleanup",
                    description=f"Enable automation {automation.entity_id}",
                    action_type="enable_automation",
                    target_id=automation.entity_id,
                    payload={"entity_id": automation.entity_id},
                    destructive=False,
                )
            )

    for name, entity_ids in name_groups.items():
        if len(entity_ids) < 2 or not name:
            continue
        actions.append(
            ChangeAction(
                action_id=new_action_id("review_duplicate_automation", name),
                category="automation_cleanup",
                description=f"Review duplicate automation names matching '{name}'",
                action_type="review_automation_duplicates",
                target_id=name,
                payload={"entity_ids": sorted(entity_ids)},
                destructive=True,
                supported=False,
                reason="Renaming, merging, or deleting automations is intentionally left as a manual review step.",
            )
        )

    if not actions:
        notes.append("No automation cleanup actions were detected from the current snapshot.")
    else:
        notes.append("Only re-enabling disabled automations is supported for automatic apply.")

    return ChangePlan(
        plan_id=new_plan_id("automation-cleanup"),
        kind="automation_cleanup",
        summary=f"Prepared {len(actions)} automation cleanup actions.",
        actions=actions,
        notes=notes,
    )


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
