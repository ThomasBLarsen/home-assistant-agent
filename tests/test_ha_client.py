from __future__ import annotations

import httpx
import pytest

from home_assistant_agent.ha_client import HomeAssistantClient


@pytest.mark.asyncio
async def test_get_config_uses_bearer_token(settings) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-token"
        assert str(request.url) == "http://example.local:8123/api/config"
        return httpx.Response(200, json={"location_name": "Home"})

    transport = httpx.MockTransport(handler)

    async with HomeAssistantClient(settings, transport=transport) as client:
        payload = await client.get_config()

    assert payload["location_name"] == "Home"


@pytest.mark.asyncio
async def test_call_service_flattens_rest_target(settings) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        data = await request.aread()
        assert request.url.path == "/api/services/automation/turn_on"
        assert b'"entity_id":"automation.morning"' in data
        assert b'"target"' not in data
        return httpx.Response(200, json=[{"changed_states": []}])

    transport = httpx.MockTransport(handler)

    async with HomeAssistantClient(settings, transport=transport) as client:
        payload = await client.call_service(
            "automation",
            "turn_on",
            target={"entity_id": "automation.morning"},
        )

    assert isinstance(payload, list)


@pytest.mark.asyncio
async def test_save_automation_config_posts_to_editor_endpoint(settings) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        data = await request.aread()
        assert request.url.path == "/api/config/automation/config/12345"
        assert b'"alias":"Leak Alert"' in data
        return httpx.Response(200, json={"result": "ok"})

    transport = httpx.MockTransport(handler)

    async with HomeAssistantClient(settings, transport=transport) as client:
        payload = await client.save_automation_config(
            "12345",
            {
                "alias": "Leak Alert",
                "description": "Test automation",
                "triggers": [],
                "conditions": [],
                "actions": [],
                "mode": "single",
            },
        )

    assert payload["result"] == "ok"


@pytest.mark.asyncio
async def test_validate_automation_config_uses_websocket_command(settings) -> None:
    async with HomeAssistantClient(settings, transport=httpx.MockTransport(lambda request: httpx.Response(500))) as client:
        async def fake_ws_command(payload: dict[str, object]) -> dict[str, object]:
            assert payload == {
                "type": "validate_config",
                "triggers": [{"trigger": "state", "entity_id": "binary_sensor.leak", "to": "on"}],
                "conditions": [],
                "actions": [{"action": "notify.notify", "data": {"message": "Leak"}}],
            }
            return {"triggers": {"valid": True, "error": None}}

        client.ws_command = fake_ws_command  # type: ignore[method-assign]

        payload = await client.validate_automation_config(
            triggers=[{"trigger": "state", "entity_id": "binary_sensor.leak", "to": "on"}],
            conditions=[],
            actions=[{"action": "notify.notify", "data": {"message": "Leak"}}],
        )

    assert payload["triggers"]["valid"] is True


@pytest.mark.asyncio
async def test_list_traces_uses_websocket_command(settings) -> None:
    async with HomeAssistantClient(settings, transport=httpx.MockTransport(lambda request: httpx.Response(500))) as client:
        async def fake_ws_command(payload: dict[str, object]) -> list[dict[str, object]]:
            assert payload == {
                "type": "trace/list",
                "domain": "automation",
                "item_id": "12345",
            }
            return [{"run_id": "abc"}]

        client.ws_command = fake_ws_command  # type: ignore[method-assign]
        payload = await client.list_traces(domain="automation", item_id="12345")

    assert payload[0]["run_id"] == "abc"


@pytest.mark.asyncio
async def test_get_trace_uses_websocket_command(settings) -> None:
    async with HomeAssistantClient(settings, transport=httpx.MockTransport(lambda request: httpx.Response(500))) as client:
        async def fake_ws_command(payload: dict[str, object]) -> dict[str, object]:
            assert payload == {
                "type": "trace/get",
                "domain": "automation",
                "item_id": "12345",
                "run_id": "run-1",
            }
            return {"run_id": "run-1", "error": "boom"}

        client.ws_command = fake_ws_command  # type: ignore[method-assign]
        payload = await client.get_trace(domain="automation", item_id="12345", run_id="run-1")

    assert payload["error"] == "boom"
