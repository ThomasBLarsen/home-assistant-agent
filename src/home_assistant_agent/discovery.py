from __future__ import annotations

import asyncio
from typing import Any

from .ha_client import HomeAssistantClient
from .models import AutomationSummary, EntitySnapshot, InventorySnapshot, utc_now_iso


def _first_present(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def _normalize_entity_registry_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "entity_id": _first_present(entry, "entity_id", "entityId", "ei"),
        "name": _first_present(entry, "name", "original_name", "en"),
        "registry_name": _first_present(entry, "name", "en"),
        "original_name": _first_present(entry, "original_name", "en"),
        "area_id": _first_present(entry, "area_id", "areaId", "ai"),
        "device_id": _first_present(entry, "device_id", "deviceId", "di"),
        "label_ids": _first_present(entry, "label_ids", "labels", "li") or [],
        "disabled_by": _first_present(entry, "disabled_by", "disabledBy", "db"),
        "hidden_by": _first_present(entry, "hidden_by", "hiddenBy", "hb"),
        "icon": _first_present(entry, "icon", "ic"),
        "platform": _first_present(entry, "platform", "pl"),
    }


async def build_inventory(client: HomeAssistantClient) -> InventorySnapshot:
    config, states, services, entity_registry, devices, areas, labels = await asyncio.gather(
        client.get_config(),
        client.get_states(),
        client.get_services(),
        client.get_entity_registry(),
        client.get_device_registry(),
        client.get_area_registry(),
        client.get_label_registry(),
    )

    registry_by_entity_id = {
        normalized["entity_id"]: normalized
        for normalized in (_normalize_entity_registry_entry(entry) for entry in entity_registry)
        if normalized["entity_id"]
    }

    entities: list[EntitySnapshot] = []
    seen_entity_ids: set[str] = set()

    for state in states:
        entity_id = state["entity_id"]
        registry_entry = registry_by_entity_id.get(entity_id, {})
        attributes = state.get("attributes", {})
        snapshot = EntitySnapshot(
            entity_id=entity_id,
            domain=entity_id.split(".", 1)[0],
            state=state.get("state"),
            friendly_name=attributes.get("friendly_name") or registry_entry.get("name"),
            area_id=registry_entry.get("area_id"),
            device_id=registry_entry.get("device_id"),
            label_ids=list(registry_entry.get("label_ids", [])),
            disabled_by=registry_entry.get("disabled_by"),
            hidden_by=registry_entry.get("hidden_by"),
            icon=attributes.get("icon") or registry_entry.get("icon"),
            platform=registry_entry.get("platform"),
            original_name=registry_entry.get("original_name"),
            registry_name=registry_entry.get("registry_name"),
            has_live_state=True,
            last_changed=state.get("last_changed"),
            last_updated=state.get("last_updated"),
            attributes=attributes,
        )
        seen_entity_ids.add(entity_id)
        entities.append(snapshot)

    for entity_id, registry_entry in registry_by_entity_id.items():
        if entity_id in seen_entity_ids:
            continue
        entities.append(
            EntitySnapshot(
                entity_id=entity_id,
                domain=entity_id.split(".", 1)[0],
                state=None,
                friendly_name=registry_entry.get("name"),
                area_id=registry_entry.get("area_id"),
                device_id=registry_entry.get("device_id"),
                label_ids=list(registry_entry.get("label_ids", [])),
                disabled_by=registry_entry.get("disabled_by"),
                hidden_by=registry_entry.get("hidden_by"),
                icon=registry_entry.get("icon"),
                platform=registry_entry.get("platform"),
                original_name=registry_entry.get("original_name"),
                registry_name=registry_entry.get("registry_name"),
                has_live_state=False,
            )
        )

    automations = [
        AutomationSummary(
            entity_id=entity.entity_id,
            name=entity.friendly_name or entity.entity_id,
            state=entity.state,
            last_triggered=entity.attributes.get("last_triggered"),
            mode=entity.attributes.get("mode"),
            current_runs=entity.attributes.get("current"),
            area_id=entity.area_id,
            is_enabled=entity.state != "off",
            attributes=entity.attributes,
        )
        for entity in entities
        if entity.domain == "automation"
    ]

    integrations = sorted(
        {
            service.get("domain")
            for service in services
            if isinstance(service, dict) and service.get("domain")
        }
        | {entity.platform for entity in entities if entity.platform}
    )

    metadata = {
        "entity_count": len(entities),
        "automation_count": len(automations),
        "device_count": len(devices),
        "area_count": len(areas),
        "label_count": len(labels),
        "service_domain_count": len(integrations),
    }

    return InventorySnapshot(
        generated_at=utc_now_iso(),
        home_assistant_config=config,
        services=services,
        entities=sorted(entities, key=lambda entity: entity.entity_id),
        automations=sorted(automations, key=lambda automation: automation.entity_id),
        devices=devices,
        areas=areas,
        labels=labels,
        integrations=integrations,
        metadata=metadata,
    )


def entity_lookup(inventory: InventorySnapshot) -> dict[str, EntitySnapshot]:
    return {entity.entity_id: entity for entity in inventory.entities}
