from __future__ import annotations

import re
from typing import Any

import yaml

from .models import InventorySnapshot


class _BlueprintInputReference(str):
    """Marker a scalar that should be emitted as a Home Assistant !input tag."""


class _BlueprintDumper(yaml.SafeDumper):
    def ignore_aliases(self, data: Any) -> bool:
        return True


def _represent_blueprint_input(dumper: yaml.SafeDumper, data: _BlueprintInputReference) -> yaml.nodes.Node:
    return dumper.represent_scalar("!input", str(data))


_BlueprintDumper.add_representer(_BlueprintInputReference, _represent_blueprint_input)


def _prepare_blueprint_yaml_value(value: Any) -> Any:
    if isinstance(value, str):
        match = re.fullmatch(r"!input\s+([A-Za-z0-9_]+)", value.strip())
        if match:
            return _BlueprintInputReference(match.group(1))
        return value
    if isinstance(value, list):
        return [_prepare_blueprint_yaml_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _prepare_blueprint_yaml_value(item) for key, item in value.items()}
    return value


def _render_blueprint_yaml(document: dict[str, Any]) -> str:
    rendered = yaml.dump(
        _prepare_blueprint_yaml_value(document),
        Dumper=_BlueprintDumper,
        sort_keys=False,
        allow_unicode=False,
    )
    return re.sub(r"!input ['\"]([A-Za-z0-9_]+)['\"]", r"!input \1", rendered)


def _normalize_trigger(trigger: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(trigger)
    if "platform" in normalized and "trigger" not in normalized:
        normalized["trigger"] = normalized.pop("platform")
    return normalized


def _normalize_action(action: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(action)
    if "service" in normalized and "action" not in normalized:
        normalized["action"] = normalized.pop("service")

    if "repeat" in normalized and isinstance(normalized["repeat"], dict):
        repeat = dict(normalized["repeat"])
        sequence = repeat.get("sequence")
        if isinstance(sequence, list):
            repeat["sequence"] = [
                _normalize_action(item) if isinstance(item, dict) else item for item in sequence
            ]
        normalized["repeat"] = repeat

    if "choose" in normalized and isinstance(normalized["choose"], list):
        normalized["choose"] = [
            {
                **option,
                "sequence": [
                    _normalize_action(item) if isinstance(item, dict) else item
                    for item in option.get("sequence", [])
                ],
            }
            for option in normalized["choose"]
            if isinstance(option, dict)
        ]

    for key in ("sequence", "parallel", "then", "else"):
        value = normalized.get(key)
        if isinstance(value, list):
            normalized[key] = [_normalize_action(item) if isinstance(item, dict) else item for item in value]

    if "wait_for_trigger" in normalized:
        wait_for_trigger = normalized["wait_for_trigger"]
        if isinstance(wait_for_trigger, list):
            normalized["wait_for_trigger"] = [
                _normalize_trigger(item) if isinstance(item, dict) else item for item in wait_for_trigger
            ]
        elif isinstance(wait_for_trigger, dict):
            normalized["wait_for_trigger"] = _normalize_trigger(wait_for_trigger)

    return normalized


def build_automation_config(
    *,
    title: str,
    intent: str,
    triggers: list[dict[str, Any]] | None = None,
    conditions: list[dict[str, Any]] | None = None,
    actions: list[dict[str, Any]] | None = None,
    mode: str = "single",
) -> dict[str, Any]:
    raw_triggers = triggers or [
        {
            "platform": "state",
            "entity_id": "replace_me.entity_id",
            "to": "replace_me_state",
        }
    ]
    raw_actions = actions or [
        {
            "action": "notify.notify",
            "data": {"message": intent},
        }
    ]

    return {
        "alias": title,
        "description": intent,
        "triggers": [_normalize_trigger(trigger) for trigger in raw_triggers],
        "conditions": conditions or [],
        "actions": [_normalize_action(action) for action in raw_actions],
        "mode": mode,
    }


def create_automation_draft(
    *,
    title: str,
    intent: str,
    triggers: list[dict[str, Any]] | None = None,
    conditions: list[dict[str, Any]] | None = None,
    actions: list[dict[str, Any]] | None = None,
    mode: str = "single",
) -> dict[str, Any]:
    automation = build_automation_config(
        title=title,
        intent=intent,
        triggers=triggers,
        conditions=conditions,
        actions=actions,
        mode=mode,
    )

    validation_notes = [
        "Replace placeholder entity IDs before applying this automation in Home Assistant.",
        "Review trigger and action schemas against the integrations in your instance.",
        "This draft is intentionally generated as YAML/JSON for review, not direct write-back.",
    ]

    return {
        "title": title,
        "intent": intent,
        "draft": automation,
        "yaml": yaml.safe_dump(automation, sort_keys=False, allow_unicode=False),
        "validation_notes": validation_notes,
    }


def build_blueprint_config(
    *,
    title: str,
    intent: str,
    inputs: dict[str, Any] | None = None,
    triggers: list[dict[str, Any]] | None = None,
    conditions: list[dict[str, Any]] | None = None,
    actions: list[dict[str, Any]] | None = None,
    mode: str = "single",
    author: str | None = None,
    source_url: str | None = None,
    min_version: str | None = None,
    variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blueprint: dict[str, Any] = {
        "name": title,
        "description": intent,
        "domain": "automation",
        "input": inputs
        or {
            "trigger_entity": {
                "name": "Trigger entity",
                "description": "Entity that should trigger this blueprint.",
                "selector": {"entity": {}},
            }
        },
    }
    if author:
        blueprint["author"] = author
    if source_url:
        blueprint["source_url"] = source_url
    if min_version:
        blueprint["homeassistant"] = {"min_version": min_version}

    document: dict[str, Any] = {
        "blueprint": blueprint,
        "triggers": [_normalize_trigger(trigger) for trigger in (triggers or [{"trigger": "state", "entity_id": "!input trigger_entity", "to": "on"}])],
        "conditions": conditions or [],
        "actions": [_normalize_action(action) for action in (actions or [{"action": "notify.notify", "data": {"message": intent}}])],
        "mode": mode,
    }
    if variables:
        document["variables"] = variables
    return document


def create_blueprint_draft(
    *,
    title: str,
    intent: str,
    inputs: dict[str, Any] | None = None,
    triggers: list[dict[str, Any]] | None = None,
    conditions: list[dict[str, Any]] | None = None,
    actions: list[dict[str, Any]] | None = None,
    mode: str = "single",
    author: str | None = None,
    source_url: str | None = None,
    min_version: str | None = None,
    variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blueprint_document = build_blueprint_config(
        title=title,
        intent=intent,
        inputs=inputs,
        triggers=triggers,
        conditions=conditions,
        actions=actions,
        mode=mode,
        author=author,
        source_url=source_url,
        min_version=min_version,
        variables=variables,
    )
    validation_notes = [
        "Blueprints are stored as YAML files under blueprints/automation/ in Home Assistant.",
        "Use !input references in triggers, variables, conditions, and actions where the blueprint should be configurable.",
        "Review selector schemas and defaults before importing the blueprint into Home Assistant.",
    ]
    return {
        "title": title,
        "intent": intent,
        "draft": blueprint_document,
        "yaml": _render_blueprint_yaml(blueprint_document),
        "validation_notes": validation_notes,
    }


def summarize_automation_health(inventory: InventorySnapshot) -> dict[str, Any]:
    enabled = sum(1 for automation in inventory.automations if automation.state != "off")
    disabled = len(inventory.automations) - enabled
    never_triggered = sum(1 for automation in inventory.automations if not automation.last_triggered)
    return {
        "total": len(inventory.automations),
        "enabled": enabled,
        "disabled": disabled,
        "never_triggered": never_triggered,
    }
