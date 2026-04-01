from __future__ import annotations

from home_assistant_agent.automations import create_blueprint_draft
from home_assistant_agent.tools import HomeAssistantAgentToolkit


def test_create_blueprint_draft_renders_input_tags() -> None:
    draft = create_blueprint_draft(
        title="Motion Alert",
        intent="Announce when motion is detected.",
        inputs={
            "motion_sensor": {
                "name": "Motion Sensor",
                "selector": {
                    "entity": {
                        "filter": [{"domain": "binary_sensor", "device_class": "motion"}]
                    }
                },
            }
        },
        triggers=[{"trigger": "state", "entity_id": "!input motion_sensor", "to": "on"}],
        actions=[{"action": "notify.notify", "data": {"message": "Motion detected"}}],
        author="Larsen",
        min_version="2024.1.0",
    )

    assert "entity_id: !input 'motion_sensor'" not in draft["yaml"]
    assert "entity_id: !input motion_sensor" in draft["yaml"]
    assert "author: Larsen" in draft["yaml"]
    assert 'min_version: 2024.1.0' in draft["yaml"]


def test_save_blueprint_writes_expected_file(settings) -> None:
    toolkit = HomeAssistantAgentToolkit(settings)

    payload = toolkit.save_blueprint(
        title="Water Leak Alert",
        intent="Alert on leaks.",
        inputs={
            "leak_sensor": {
                "name": "Leak Sensor",
                "selector": {"entity": {"filter": [{"domain": "binary_sensor", "device_class": "moisture"}]}},
            }
        },
        triggers=[{"trigger": "state", "entity_id": "!input leak_sensor", "to": "on"}],
        actions=[{"action": "notify.notify", "data": {"message": "Leak detected"}}],
        author="Larsen",
    )

    assert payload["ok"] is True
    assert payload["created"] is True
    assert payload["relative_path"] == "blueprints\\automation\\larsen\\water_leak_alert.yaml"
    saved_text = (settings.workspace_dir / payload["relative_path"]).read_text(encoding="utf-8")
    assert "entity_id: !input leak_sensor" in saved_text


def test_save_blueprint_refuses_to_overwrite_without_flag(settings) -> None:
    toolkit = HomeAssistantAgentToolkit(settings)

    first = toolkit.save_blueprint(
        title="Repeated Blueprint",
        intent="First version.",
        author="Larsen",
    )
    second = toolkit.save_blueprint(
        title="Repeated Blueprint",
        intent="Second version.",
        author="Larsen",
    )

    assert first["ok"] is True
    assert second["ok"] is False
    assert "overwrite=True" in second["error"]
