from __future__ import annotations

import pytest

from home_assistant_agent.tools import HomeAssistantAgentToolkit


class FakeHomeAssistantClient:
    def __init__(self, validation_result, initial_states=None, traces=None, full_trace=None) -> None:
        self.validation_result = validation_result
        self.initial_states = initial_states or []
        self.traces = traces or []
        self.full_trace = full_trace or {}
        self.saved_automation_id: str | None = None
        self.saved_config: dict | None = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def validate_automation_config(self, *, triggers, conditions, actions):
        self.last_validation = {
            "triggers": triggers,
            "conditions": conditions,
            "actions": actions,
        }
        return self.validation_result

    async def save_automation_config(self, automation_id: str, config: dict):
        self.saved_automation_id = automation_id
        self.saved_config = config
        return {"result": "ok"}

    async def get_states(self):
        if self.saved_automation_id and self.saved_config:
            return [
                {
                    "entity_id": "automation.vannlekkasje_varsling",
                    "attributes": {
                        "id": self.saved_automation_id,
                        "friendly_name": self.saved_config["alias"],
                    },
                }
            ]
        return self.initial_states

    async def list_traces(self, *, domain: str, item_id: str):
        self.last_trace_list = {"domain": domain, "item_id": item_id}
        return self.traces

    async def get_trace(self, *, domain: str, item_id: str, run_id: str):
        self.last_trace_get = {"domain": domain, "item_id": item_id, "run_id": run_id}
        return self.full_trace


@pytest.mark.asyncio
async def test_save_automation_creates_new_automation(monkeypatch, settings) -> None:
    fake_client = FakeHomeAssistantClient(
        validation_result={
            "triggers": {"valid": True, "error": None},
            "conditions": {"valid": True, "error": None},
            "actions": {"valid": True, "error": None},
        }
    )
    monkeypatch.setattr(
        "home_assistant_agent.tools.HomeAssistantClient",
        lambda current_settings: fake_client,
    )

    toolkit = HomeAssistantAgentToolkit(settings)
    payload = await toolkit.save_automation(
        title="Vannlekkasje varsling",
        intent="Varsler Larsen ved lekkasje.",
        triggers=[{"platform": "state", "entity_id": "binary_sensor.leak", "to": "on"}],
        actions=[{"service": "notify.notify", "data": {"message": "Lekasje"}}],
        mode="restart",
    )

    assert payload["ok"] is True
    assert payload["created"] is True
    assert payload["entity_id"] == "automation.vannlekkasje_varsling"
    assert fake_client.saved_config["triggers"][0]["trigger"] == "state"
    assert "platform" not in fake_client.saved_config["triggers"][0]
    assert fake_client.saved_config["actions"][0]["action"] == "notify.notify"
    assert "service" not in fake_client.saved_config["actions"][0]


@pytest.mark.asyncio
async def test_save_automation_updates_by_entity_id(monkeypatch, settings) -> None:
    fake_client = FakeHomeAssistantClient(
        validation_result={
            "triggers": {"valid": True, "error": None},
            "conditions": {"valid": True, "error": None},
            "actions": {"valid": True, "error": None},
        },
        initial_states=[
            {
                "entity_id": "automation.vannlekkasje_varsling",
                "attributes": {"id": "existing-id", "friendly_name": "Vannlekkasje varsling"},
            }
        ],
    )
    monkeypatch.setattr(
        "home_assistant_agent.tools.HomeAssistantClient",
        lambda current_settings: fake_client,
    )

    toolkit = HomeAssistantAgentToolkit(settings)
    payload = await toolkit.save_automation(
        title="Vannlekkasje varsling",
        intent="Oppdatert lekkasjevarsel.",
        actions=[{"action": "notify.notify", "data": {"message": "Oppdatert"}}],
        entity_id="automation.vannlekkasje_varsling",
    )

    assert payload["ok"] is True
    assert payload["created"] is False
    assert payload["automation_id"] == "existing-id"
    assert fake_client.saved_automation_id == "existing-id"


@pytest.mark.asyncio
async def test_save_automation_returns_validation_errors(monkeypatch, settings) -> None:
    fake_client = FakeHomeAssistantClient(
        validation_result={
            "triggers": {"valid": False, "error": "Bad trigger"},
            "conditions": {"valid": True, "error": None},
            "actions": {"valid": True, "error": None},
        }
    )
    monkeypatch.setattr(
        "home_assistant_agent.tools.HomeAssistantClient",
        lambda current_settings: fake_client,
    )

    toolkit = HomeAssistantAgentToolkit(settings)
    payload = await toolkit.save_automation(
        title="Broken automation",
        intent="Should fail validation.",
        triggers=[{"trigger": "bad"}],
    )

    assert payload["ok"] is False
    assert payload["error"] == "Automation config failed validation."
    assert fake_client.saved_config is None


@pytest.mark.asyncio
async def test_inspect_automation_trace_detects_manual_trigger_to_state_issue(monkeypatch, settings) -> None:
    fake_client = FakeHomeAssistantClient(
        validation_result={},
        initial_states=[
            {
                "entity_id": "automation.vannlekkasje_varsling",
                "attributes": {"id": "1774994336122", "friendly_name": "Vannlekkasje varsling"},
            }
        ],
        traces=[
            {
                "run_id": "run-1",
                "last_step": "action/0",
                "error": "UndefinedError: 'dict object' has no attribute 'to_state'",
            }
        ],
        full_trace={
            "last_step": "action/0",
            "error": "UndefinedError: 'dict object' has no attribute 'to_state'",
            "trace": {
                "trigger": [
                    {
                        "changed_variables": {
                            "trigger": {"platform": None},
                        }
                    }
                ],
                "action/0": [
                    {
                        "error": "UndefinedError: 'dict object' has no attribute 'to_state'",
                    }
                ],
            },
        },
    )
    monkeypatch.setattr(
        "home_assistant_agent.tools.HomeAssistantClient",
        lambda current_settings: fake_client,
    )

    toolkit = HomeAssistantAgentToolkit(settings)
    payload = await toolkit.inspect_automation_trace(entity_id="automation.vannlekkasje_varsling")

    assert payload["ok"] is True
    assert payload["analysis"]["last_step"] == "action/0"
    assert "trigger.to_state" in payload["analysis"]["fix_suggestion"]
    assert "manual" in payload["analysis"]["root_cause"].lower()


@pytest.mark.asyncio
async def test_list_automation_traces_uses_resolved_automation_id(monkeypatch, settings) -> None:
    fake_client = FakeHomeAssistantClient(
        validation_result={},
        initial_states=[
            {
                "entity_id": "automation.vannlekkasje_varsling",
                "attributes": {"id": "1774994336122", "friendly_name": "Vannlekkasje varsling"},
            }
        ],
        traces=[{"run_id": "run-1"}],
    )
    monkeypatch.setattr(
        "home_assistant_agent.tools.HomeAssistantClient",
        lambda current_settings: fake_client,
    )

    toolkit = HomeAssistantAgentToolkit(settings)
    payload = await toolkit.list_automation_traces(entity_id="automation.vannlekkasje_varsling")

    assert payload["ok"] is True
    assert payload["automation_id"] == "1774994336122"
    assert payload["trace_count"] == 1
