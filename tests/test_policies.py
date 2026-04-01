from __future__ import annotations

from home_assistant_agent.models import ChangeAction, ChangePlan
from home_assistant_agent.policies import PolicyEngine


def test_policy_blocks_destructive_and_unknown_actions(settings) -> None:
    engine = PolicyEngine(settings)
    plan = ChangePlan(
        plan_id="plan-123",
        kind="entity_cleanup",
        summary="Test plan",
        actions=[
            ChangeAction(
                action_id="a1",
                category="entity_cleanup",
                description="Delete an entity",
                action_type="delete_entity",
                target_id="sensor.test",
                destructive=True,
            ),
            ChangeAction(
                action_id="a2",
                category="entity_cleanup",
                description="Review manually",
                action_type="review_entity",
                target_id="sensor.other",
            ),
        ],
    )

    evaluated = engine.evaluate_plan(plan)

    assert evaluated.approval_code == engine.approval_code("plan-123")
    assert all(not action.supported for action in evaluated.actions)


def test_policy_verifies_approval_code(settings) -> None:
    engine = PolicyEngine(settings)
    code = engine.approval_code("plan-abc")

    assert engine.verify_approval("plan-abc", code) is True
    assert engine.verify_approval("plan-abc", "wrong-code") is False
