from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from .automations import (
    build_automation_config,
    create_automation_draft,
    create_blueprint_draft,
    summarize_automation_health,
)
from .config import Settings, load_settings
from .diagnostics import find_issues, preview_automation_cleanup, preview_entity_cleanup
from .discovery import build_inventory
from .ha_client import HomeAssistantClient
from .models import ApplyResult, ChangePlan
from .policies import PolicyEngine
from .storage import append_jsonl, load_change_plan, save_change_plan, write_json


class HomeAssistantAgentToolkit:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.policy = PolicyEngine(self.settings)

    async def scan_home_assistant(self) -> dict[str, Any]:
        async with HomeAssistantClient(self.settings) as client:
            inventory = await build_inventory(client)
        snapshot = inventory.to_dict()
        write_json(self.settings.logs_dir / "inventory-latest.json", snapshot)
        return {
            "ok": True,
            "inventory": snapshot,
            "automation_health": summarize_automation_health(inventory),
        }

    async def list_entities(
        self,
        *,
        domain: str | None = None,
        area_id: str | None = None,
        state: str | None = None,
    ) -> dict[str, Any]:
        async with HomeAssistantClient(self.settings) as client:
            inventory = await build_inventory(client)

        entities = inventory.entities
        if domain:
            entities = [entity for entity in entities if entity.domain == domain]
        if area_id:
            entities = [entity for entity in entities if entity.area_id == area_id]
        if state:
            entities = [entity for entity in entities if entity.state == state]

        return {
            "ok": True,
            "count": len(entities),
            "entities": [entity.to_dict() for entity in entities],
        }

    async def find_issues(self) -> dict[str, Any]:
        async with HomeAssistantClient(self.settings) as client:
            inventory = await build_inventory(client)
        issues = [issue.to_dict() for issue in find_issues(inventory)]
        payload = {"ok": True, "issue_count": len(issues), "issues": issues}
        write_json(self.settings.logs_dir / "issues-latest.json", payload)
        return payload

    async def preview_entity_cleanup(self) -> dict[str, Any]:
        async with HomeAssistantClient(self.settings) as client:
            inventory = await build_inventory(client)
        plan = self.policy.evaluate_plan(preview_entity_cleanup(inventory))
        path = self._save_plan(plan)
        return {
            "ok": True,
            "plan": plan.to_dict(),
            "saved_to": str(path),
        }

    async def preview_automation_cleanup(self) -> dict[str, Any]:
        async with HomeAssistantClient(self.settings) as client:
            inventory = await build_inventory(client)
        plan = self.policy.evaluate_plan(preview_automation_cleanup(inventory))
        path = self._save_plan(plan)
        return {
            "ok": True,
            "plan": plan.to_dict(),
            "saved_to": str(path),
        }

    def create_automation_draft(
        self,
        *,
        title: str,
        intent: str,
        triggers: list[dict[str, Any]] | None = None,
        conditions: list[dict[str, Any]] | None = None,
        actions: list[dict[str, Any]] | None = None,
        mode: str = "single",
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "draft": create_automation_draft(
                title=title,
                intent=intent,
                triggers=triggers,
                conditions=conditions,
                actions=actions,
                mode=mode,
            ),
        }

    def create_blueprint_draft(
        self,
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
        return {
            "ok": True,
            "draft": create_blueprint_draft(
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
            ),
        }

    def save_blueprint(
        self,
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
        relative_path: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        draft = create_blueprint_draft(
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
        try:
            target_path = self._resolve_blueprint_path(title, author=author, relative_path=relative_path)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        existed = target_path.exists()
        if existed and not overwrite:
            return {
                "ok": False,
                "error": f"Blueprint file already exists at '{target_path}'. Pass overwrite=True to replace it.",
                "saved_to": str(target_path),
            }

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(draft["yaml"], encoding="utf-8")
        payload = {
            "ok": True,
            "created": not existed,
            "saved_to": str(target_path),
            "relative_path": str(target_path.relative_to(self.settings.workspace_dir)),
            "draft": draft,
        }
        self._audit("save_blueprint", payload)
        return payload

    async def validate_automation_config(
        self,
        *,
        title: str,
        intent: str,
        triggers: list[dict[str, Any]] | None = None,
        conditions: list[dict[str, Any]] | None = None,
        actions: list[dict[str, Any]] | None = None,
        mode: str = "single",
    ) -> dict[str, Any]:
        config = build_automation_config(
            title=title,
            intent=intent,
            triggers=triggers,
            conditions=conditions,
            actions=actions,
            mode=mode,
        )

        async with HomeAssistantClient(self.settings) as client:
            validation = await client.validate_automation_config(
                triggers=config["triggers"],
                conditions=config["conditions"],
                actions=config["actions"],
            )

        payload = {
            "ok": True,
            "valid": self._automation_validation_ok(validation),
            "validation": validation,
            "config": config,
        }
        self._audit("validate_automation_config", payload)
        return payload

    async def save_automation(
        self,
        *,
        title: str,
        intent: str,
        triggers: list[dict[str, Any]] | None = None,
        conditions: list[dict[str, Any]] | None = None,
        actions: list[dict[str, Any]] | None = None,
        mode: str = "single",
        automation_id: str | None = None,
        entity_id: str | None = None,
    ) -> dict[str, Any]:
        if automation_id and entity_id:
            return {"ok": False, "error": "Pass either automation_id or entity_id, not both."}

        config = build_automation_config(
            title=title,
            intent=intent,
            triggers=triggers,
            conditions=conditions,
            actions=actions,
            mode=mode,
        )

        async with HomeAssistantClient(self.settings) as client:
            validation = await client.validate_automation_config(
                triggers=config["triggers"],
                conditions=config["conditions"],
                actions=config["actions"],
            )
            if not self._automation_validation_ok(validation):
                return {
                    "ok": False,
                    "error": "Automation config failed validation.",
                    "validation": validation,
                    "config": config,
                }

            resolved_automation_id, created = await self._resolve_automation_id(
                client,
                automation_id=automation_id,
                entity_id=entity_id,
            )
            if not resolved_automation_id:
                return {
                    "ok": False,
                    "error": f"Could not resolve automation ID for entity '{entity_id}'.",
                    "validation": validation,
                    "config": config,
                }

            result = await client.save_automation_config(resolved_automation_id, config)
            saved_state = await self._find_automation_state(client, resolved_automation_id)

        payload = {
            "ok": True,
            "created": created,
            "automation_id": resolved_automation_id,
            "entity_id": saved_state["entity_id"] if saved_state else None,
            "alias": config["alias"],
            "validation": validation,
            "result": result,
            "config": config,
        }
        self._audit("save_automation", payload)
        return payload

    async def list_automation_traces(
        self,
        *,
        automation_id: str | None = None,
        entity_id: str | None = None,
    ) -> dict[str, Any]:
        if automation_id and entity_id:
            return {"ok": False, "error": "Pass either automation_id or entity_id, not both."}

        async with HomeAssistantClient(self.settings) as client:
            resolved_automation_id, resolved_entity_id = await self._resolve_automation_target(
                client,
                automation_id=automation_id,
                entity_id=entity_id,
            )
            if not resolved_automation_id:
                return {"ok": False, "error": "Could not resolve the target automation."}
            traces = await client.list_traces(domain="automation", item_id=resolved_automation_id)

        payload = {
            "ok": True,
            "automation_id": resolved_automation_id,
            "entity_id": resolved_entity_id,
            "trace_count": len(traces),
            "traces": traces,
        }
        self._audit("list_automation_traces", payload)
        return payload

    async def inspect_automation_trace(
        self,
        *,
        automation_id: str | None = None,
        entity_id: str | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        if automation_id and entity_id:
            return {"ok": False, "error": "Pass either automation_id or entity_id, not both."}

        async with HomeAssistantClient(self.settings) as client:
            resolved_automation_id, resolved_entity_id = await self._resolve_automation_target(
                client,
                automation_id=automation_id,
                entity_id=entity_id,
            )
            if not resolved_automation_id:
                return {"ok": False, "error": "Could not resolve the target automation."}

            traces = await client.list_traces(domain="automation", item_id=resolved_automation_id)
            if not traces:
                return {
                    "ok": False,
                    "error": "No traces found for this automation.",
                    "automation_id": resolved_automation_id,
                    "entity_id": resolved_entity_id,
                }

            selected_trace = self._select_trace(traces, run_id=run_id)
            if not selected_trace:
                return {
                    "ok": False,
                    "error": f"Trace run '{run_id}' was not found for this automation.",
                    "automation_id": resolved_automation_id,
                    "entity_id": resolved_entity_id,
                }

            full_trace = await client.get_trace(
                domain="automation",
                item_id=resolved_automation_id,
                run_id=selected_trace["run_id"],
            )

        analysis = self._analyze_automation_trace(full_trace)
        payload = {
            "ok": True,
            "automation_id": resolved_automation_id,
            "entity_id": resolved_entity_id,
            "trace_summary": selected_trace,
            "trace": full_trace,
            "analysis": analysis,
        }
        self._audit("inspect_automation_trace", payload)
        return payload

    async def apply_change_plan(self, plan_id: str, approval_code: str | None = None) -> dict[str, Any]:
        raw_plan = load_change_plan(self.settings.change_plan_dir, plan_id)
        if raw_plan.get("requires_confirmation") and not self.policy.verify_approval(plan_id, approval_code):
            return {
                "ok": False,
                "error": "Approval code is required and did not match the stored plan.",
            }

        applied_actions: list[dict[str, Any]] = []
        skipped_actions: list[dict[str, Any]] = []

        async with HomeAssistantClient(self.settings) as client:
            for action in raw_plan.get("actions", []):
                if not action.get("supported"):
                    skipped_actions.append(
                        {
                            "action_id": action["action_id"],
                            "reason": action.get("reason", "Unsupported action."),
                        }
                    )
                    continue

                action_type = action["action_type"]
                target_id = action["target_id"]

                if action_type == "disable_entity":
                    result = await client.set_entity_disabled(target_id, True)
                elif action_type == "enable_automation":
                    result = await client.call_service(
                        "automation",
                        "turn_on",
                        target={"entity_id": target_id},
                    )
                else:
                    skipped_actions.append(
                        {
                            "action_id": action["action_id"],
                            "reason": f"Unsupported action type '{action_type}'.",
                        }
                    )
                    continue

                applied_actions.append(
                    {
                        "action_id": action["action_id"],
                        "action_type": action_type,
                        "target_id": target_id,
                        "result": result,
                    }
                )

        result = ApplyResult(
            plan_id=plan_id,
            applied_actions=applied_actions,
            skipped_actions=skipped_actions,
            approval_verified=True,
        ).to_dict()
        self._audit("apply_change_plan", result)
        return {"ok": True, "result": result}

    async def call_service_safe(
        self,
        *,
        domain: str,
        service: str,
        service_data: dict[str, Any] | None = None,
        target: dict[str, Any] | None = None,
        return_response: bool = False,
    ) -> dict[str, Any]:
        allowed, reason = self.policy.can_call_service(domain)
        if not allowed:
            return {"ok": False, "error": reason}

        async with HomeAssistantClient(self.settings) as client:
            result = await client.call_service(
                domain,
                service,
                service_data=service_data,
                target=target,
                return_response=return_response,
            )

        payload = {
            "ok": True,
            "domain": domain,
            "service": service,
            "result": result,
        }
        self._audit("call_service_safe", payload)
        return payload

    def _save_plan(self, plan: ChangePlan) -> Path:
        path = save_change_plan(self.settings.change_plan_dir, plan)
        self._audit(
            "preview_plan",
            {
                "plan_id": plan.plan_id,
                "kind": plan.kind,
                "action_count": len(plan.actions),
                "saved_to": str(path),
            },
        )
        return path

    def _audit(self, event_type: str, payload: dict[str, Any]) -> None:
        append_jsonl(
            self.settings.audit_log_path,
            {"event_type": event_type, "payload": payload},
        )

    @staticmethod
    def _automation_validation_ok(validation: dict[str, Any]) -> bool:
        return all(check.get("valid") for check in validation.values() if isinstance(check, dict))

    async def _resolve_automation_id(
        self,
        client: HomeAssistantClient,
        *,
        automation_id: str | None,
        entity_id: str | None,
    ) -> tuple[str | None, bool]:
        if automation_id:
            return automation_id, False
        if entity_id:
            saved_state = await self._find_automation_state(client, entity_id=entity_id)
            if not saved_state:
                return None, False
            resolved_automation_id = saved_state.get("attributes", {}).get("id")
            if not resolved_automation_id:
                return None, False
            return str(resolved_automation_id), False
        return str(int(time.time() * 1000)), True

    async def _resolve_automation_target(
        self,
        client: HomeAssistantClient,
        *,
        automation_id: str | None,
        entity_id: str | None,
    ) -> tuple[str | None, str | None]:
        if automation_id:
            saved_state = await self._find_automation_state(client, automation_id=automation_id)
            return automation_id, saved_state["entity_id"] if saved_state else None
        if entity_id:
            saved_state = await self._find_automation_state(client, entity_id=entity_id)
            if not saved_state:
                return None, entity_id
            resolved_automation_id = saved_state.get("attributes", {}).get("id")
            return (str(resolved_automation_id) if resolved_automation_id is not None else None), entity_id
        return None, None

    async def _find_automation_state(
        self,
        client: HomeAssistantClient,
        automation_id: str | None = None,
        entity_id: str | None = None,
    ) -> dict[str, Any] | None:
        states = await client.get_states()
        for state in states:
            if not state["entity_id"].startswith("automation."):
                continue
            if entity_id and state["entity_id"] == entity_id:
                return state
            state_automation_id = state.get("attributes", {}).get("id")
            if automation_id and str(state_automation_id) == str(automation_id):
                return state
        return None

    @staticmethod
    def _select_trace(traces: list[dict[str, Any]], *, run_id: str | None) -> dict[str, Any] | None:
        if run_id:
            for trace in traces:
                if trace.get("run_id") == run_id:
                    return trace
            return None
        return traces[0] if traces else None

    @staticmethod
    def _analyze_automation_trace(trace: dict[str, Any]) -> dict[str, Any]:
        last_step = trace.get("last_step")
        error = trace.get("error")
        trace_steps = trace.get("trace", {})
        last_step_entries = trace_steps.get(last_step, []) if isinstance(trace_steps, dict) and last_step else []
        last_step_error = None
        if isinstance(last_step_entries, list) and last_step_entries:
            last_step_error = last_step_entries[-1].get("error")

        analysis = {
            "last_step": last_step,
            "error": error or last_step_error,
            "root_cause": None,
            "fix_suggestion": None,
        }

        trigger_info = None
        trigger_entries = trace_steps.get("trigger", []) if isinstance(trace_steps, dict) else []
        if isinstance(trigger_entries, list) and trigger_entries:
            trigger_info = trigger_entries[-1].get("changed_variables", {}).get("trigger")

        if (
            isinstance(analysis["error"], str)
            and "to_state" in analysis["error"]
            and isinstance(trigger_info, dict)
            and trigger_info.get("platform") is None
        ):
            analysis["root_cause"] = (
                "The automation was run manually or without a state trigger payload, so 'trigger.to_state' was missing."
            )
            analysis["fix_suggestion"] = (
                "Guard templates that read trigger.to_state with a fallback for manual runs, "
                "for example by checking that trigger.to_state is defined before using it."
            )
            return analysis

        if analysis["error"]:
            analysis["root_cause"] = "Home Assistant reported a runtime error in the trace."
            analysis["fix_suggestion"] = "Inspect the failing step and any templates or service data referenced there."
        else:
            analysis["root_cause"] = "No explicit runtime error was captured."
            analysis["fix_suggestion"] = "Review the selected trace summary and step results."
        return analysis

    def _resolve_blueprint_path(
        self,
        title: str,
        *,
        author: str | None,
        relative_path: str | None,
    ) -> Path:
        workspace_root = self.settings.workspace_dir.resolve()
        if relative_path:
            candidate = (self.settings.workspace_dir / relative_path).resolve()
            if workspace_root != candidate and workspace_root not in candidate.parents:
                raise ValueError("Blueprint path must stay within the workspace directory.")
            return candidate

        author_folder = self._slugify(author or "home_assistant_agent")
        filename = f"{self._slugify(title)}.yaml"
        return workspace_root / "blueprints" / "automation" / author_folder / filename

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
        return slug or "blueprint"
