from __future__ import annotations

from home_assistant_agent.diagnostics import find_issues, preview_automation_cleanup, preview_entity_cleanup
from home_assistant_agent.models import AutomationSummary, EntitySnapshot, InventorySnapshot
from home_assistant_agent.policies import PolicyEngine


def test_preview_entity_cleanup_flags_unhealthy_entities(settings) -> None:
    inventory = InventorySnapshot(
        generated_at="2026-03-31T00:00:00+00:00",
        home_assistant_config={},
        services=[],
        entities=[
            EntitySnapshot(
                entity_id="sensor.dead_battery",
                domain="sensor",
                state="unavailable",
                friendly_name="Dead Battery",
            )
        ],
        automations=[],
        devices=[],
        areas=[],
        labels=[],
        integrations=[],
    )

    plan = PolicyEngine(settings).evaluate_plan(preview_entity_cleanup(inventory))

    assert len(plan.actions) == 1
    assert plan.actions[0].action_type == "disable_entity"
    assert plan.actions[0].supported is True
    assert plan.approval_code is not None


def test_find_issues_and_preview_automation_cleanup(settings) -> None:
    inventory = InventorySnapshot(
        generated_at="2026-03-31T00:00:00+00:00",
        home_assistant_config={},
        services=[],
        entities=[],
        automations=[
            AutomationSummary(
                entity_id="automation.morning_routine",
                name="Morning Routine",
                state="off",
                last_triggered=None,
                mode="single",
                current_runs=0,
            )
        ],
        devices=[],
        areas=[],
        labels=[],
        integrations=[],
    )

    issues = find_issues(inventory)
    plan = PolicyEngine(settings).evaluate_plan(preview_automation_cleanup(inventory))

    assert any(issue.category == "automation_disabled" for issue in issues)
    assert any(action.action_type == "enable_automation" for action in plan.actions)
