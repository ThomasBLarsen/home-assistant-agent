from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

import httpx
import websockets

from .config import Settings


class HomeAssistantApiError(RuntimeError):
    """Raised when Home Assistant rejects a request."""


class HomeAssistantClient:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self._http = httpx.AsyncClient(
            base_url=self.settings.api_base_url,
            headers={"Authorization": f"Bearer {self.settings.home_assistant_token}"},
            timeout=self.settings.request_timeout_seconds,
            transport=transport,
        )
        self._ws = None
        self._ws_lock = asyncio.Lock()
        self._next_message_id = 1

    async def __aenter__(self) -> HomeAssistantClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
        await self._http.aclose()

    async def rest_get(self, path: str) -> Any:
        response = await self._http.get(path)
        self._raise_for_status(response)
        return response.json()

    async def rest_post(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        response = await self._http.post(path, json=payload or {})
        self._raise_for_status(response)
        if not response.content:
            return None
        return response.json()

    async def ping(self) -> Any:
        return await self.rest_get("/")

    async def get_config(self) -> dict[str, Any]:
        return await self.rest_get("/config")

    async def get_states(self) -> list[dict[str, Any]]:
        return await self.rest_get("/states")

    async def get_services(self) -> list[dict[str, Any]]:
        return await self.rest_get("/services")

    async def save_automation_config(self, automation_id: str, config: dict[str, Any]) -> Any:
        return await self.rest_post(f"/config/automation/config/{automation_id}", config)

    async def list_traces(self, *, domain: str, item_id: str) -> list[dict[str, Any]]:
        result = await self.ws_command(
            {
                "type": "trace/list",
                "domain": domain,
                "item_id": item_id,
            }
        )
        return result if isinstance(result, list) else []

    async def get_trace(self, *, domain: str, item_id: str, run_id: str) -> dict[str, Any]:
        result = await self.ws_command(
            {
                "type": "trace/get",
                "domain": domain,
                "item_id": item_id,
                "run_id": run_id,
            }
        )
        return result if isinstance(result, dict) else {}

    async def validate_automation_config(
        self,
        *,
        triggers: list[dict[str, Any]],
        conditions: list[dict[str, Any]],
        actions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return await self.ws_command(
            {
                "type": "validate_config",
                "triggers": triggers,
                "conditions": conditions,
                "actions": actions,
            }
        )

    async def call_service(
        self,
        domain: str,
        service: str,
        service_data: dict[str, Any] | None = None,
        target: dict[str, Any] | None = None,
        *,
        return_response: bool = False,
    ) -> Any:
        payload = dict(service_data or {})
        if target:
            payload.update(target)
        if return_response:
            return await self.ws_command(
                {
                    "type": "call_service",
                    "domain": domain,
                    "service": service,
                    "service_data": service_data or {},
                    "target": target or {},
                    "return_response": True,
                }
            )
        return await self.rest_post(f"/services/{domain}/{service}", payload)

    async def get_entity_registry(self) -> list[dict[str, Any]]:
        try:
            result = await self.ws_command({"type": "config/entity_registry/list"})
            if isinstance(result, list):
                return result
        except HomeAssistantApiError:
            pass

        fallback = await self.ws_command({"type": "config/entity_registry/list_for_display"})
        entities = fallback.get("entities", []) if isinstance(fallback, dict) else []
        return [
            {
                "entity_id": entity.get("ei"),
                "name": entity.get("en"),
                "original_name": entity.get("en"),
                "disabled_by": None,
                "platform": None,
            }
            for entity in entities
            if entity.get("ei")
        ]

    async def get_device_registry(self) -> list[dict[str, Any]]:
        return await self._safe_ws_list("config/device_registry/list")

    async def get_area_registry(self) -> list[dict[str, Any]]:
        return await self._safe_ws_list("config/area_registry/list")

    async def get_label_registry(self) -> list[dict[str, Any]]:
        return await self._safe_ws_list("config/label_registry/list")

    async def extract_from_target(
        self, target: dict[str, Any], *, expand_group: bool = True
    ) -> dict[str, Any]:
        return await self.ws_command(
            {
                "type": "extract_from_target",
                "target": target,
                "expand_group": expand_group,
            }
        )

    async def set_entity_disabled(self, entity_id: str, disabled: bool) -> dict[str, Any]:
        return await self.ws_command(
            {
                "type": "config/entity_registry/update",
                "entity_id": entity_id,
                "disabled_by": "user" if disabled else None,
            }
        )

    async def ws_command(self, payload: dict[str, Any]) -> Any:
        async with self._ws_lock:
            websocket = await self._ensure_ws()
            message_id = self._next_message_id
            self._next_message_id += 1

            request = {"id": message_id, **payload}
            await websocket.send(json.dumps(request))

            while True:
                raw_message = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=self.settings.websocket_timeout_seconds,
                )
                response = json.loads(raw_message)
                if response.get("id") != message_id:
                    continue
                if response.get("type") == "result":
                    if response.get("success"):
                        return response.get("result")
                    raise HomeAssistantApiError(response.get("error", {}).get("message", "Unknown WebSocket error."))
                if response.get("type") == "event":
                    return response.get("event")
                raise HomeAssistantApiError(f"Unexpected WebSocket response: {response}")

    async def subscribe_events(
        self,
        *,
        event_type: str | None = None,
        max_events: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        websocket = await self._open_authenticated_websocket()
        try:
            subscribe_message: dict[str, Any] = {"id": 1, "type": "subscribe_events"}
            if event_type:
                subscribe_message["event_type"] = event_type
            await websocket.send(json.dumps(subscribe_message))

            confirmation = json.loads(
                await asyncio.wait_for(
                    websocket.recv(),
                    timeout=self.settings.websocket_timeout_seconds,
                )
            )
            if not confirmation.get("success"):
                raise HomeAssistantApiError(
                    confirmation.get("error", {}).get("message", "Subscription failed.")
                )

            seen = 0
            while max_events is None or seen < max_events:
                raw_event = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=self.settings.websocket_timeout_seconds,
                )
                event = json.loads(raw_event)
                if event.get("type") == "event":
                    seen += 1
                    yield event.get("event", {})
        finally:
            await websocket.close()

    async def _safe_ws_list(self, command_type: str) -> list[dict[str, Any]]:
        try:
            result = await self.ws_command({"type": command_type})
            if isinstance(result, list):
                return result
        except HomeAssistantApiError:
            return []
        return []

    async def _ensure_ws(self):
        if self._ws is None or getattr(self._ws, "closed", False):
            self._ws = await self._open_authenticated_websocket()
        return self._ws

    async def _open_authenticated_websocket(self):
        websocket = await websockets.connect(self._websocket_url(), max_size=None)
        auth_required = json.loads(
            await asyncio.wait_for(
                websocket.recv(),
                timeout=self.settings.websocket_timeout_seconds,
            )
        )
        if auth_required.get("type") != "auth_required":
            await websocket.close()
            raise HomeAssistantApiError("Home Assistant did not request WebSocket authentication.")

        await websocket.send(
            json.dumps(
                {
                    "type": "auth",
                    "access_token": self.settings.home_assistant_token,
                }
            )
        )
        auth_response = json.loads(
            await asyncio.wait_for(
                websocket.recv(),
                timeout=self.settings.websocket_timeout_seconds,
            )
        )
        if auth_response.get("type") != "auth_ok":
            await websocket.close()
            raise HomeAssistantApiError(auth_response.get("message", "WebSocket authentication failed."))
        return websocket

    def _websocket_url(self) -> str:
        url = self.settings.home_assistant_url.rstrip("/")
        if url.startswith("https://"):
            url = "wss://" + url[len("https://") :]
        elif url.startswith("http://"):
            url = "ws://" + url[len("http://") :]
        return f"{url}/api/websocket"

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HomeAssistantApiError(exc.response.text) from exc
