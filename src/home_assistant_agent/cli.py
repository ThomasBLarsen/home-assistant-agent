from __future__ import annotations

import asyncio
import json
from typing import Any

import typer

from .tools import HomeAssistantAgentToolkit

app = typer.Typer(help="Guarded AI tooling for Home Assistant.")


def _parse_json(value: str | None) -> dict[str, Any] | list[dict[str, Any]] | None:
    if not value:
        return None
    return json.loads(value)


def _print(payload: dict[str, Any]) -> None:
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@app.command("scan")
def scan_command() -> None:
    """Build an inventory snapshot from Home Assistant."""
    toolkit = HomeAssistantAgentToolkit()
    _print(asyncio.run(toolkit.scan_home_assistant()))


@app.command("list-entities")
def list_entities_command(
    domain: str | None = typer.Option(None, help="Filter by entity domain."),
    area_id: str | None = typer.Option(None, help="Filter by area ID."),
    state: str | None = typer.Option(None, help="Filter by current state."),
) -> None:
    """List entities from the current Home Assistant snapshot."""
    toolkit = HomeAssistantAgentToolkit()
    _print(asyncio.run(toolkit.list_entities(domain=domain, area_id=area_id, state=state)))


@app.command("issues")
def issues_command() -> None:
    """Run diagnostic checks on the current Home Assistant inventory."""
    toolkit = HomeAssistantAgentToolkit()
    _print(asyncio.run(toolkit.find_issues()))


@app.command("preview-entity-cleanup")
def preview_entity_cleanup_command() -> None:
    """Create a guarded entity cleanup plan."""
    toolkit = HomeAssistantAgentToolkit()
    _print(asyncio.run(toolkit.preview_entity_cleanup()))


@app.command("preview-automation-cleanup")
def preview_automation_cleanup_command() -> None:
    """Create a guarded automation cleanup plan."""
    toolkit = HomeAssistantAgentToolkit()
    _print(asyncio.run(toolkit.preview_automation_cleanup()))


@app.command("apply-plan")
def apply_plan_command(
    plan_id: str = typer.Argument(..., help="Saved plan ID."),
    approve: str = typer.Option(..., "--approve", help="Approval code returned with the preview plan."),
) -> None:
    """Apply a previously previewed change plan."""
    toolkit = HomeAssistantAgentToolkit()
    _print(asyncio.run(toolkit.apply_change_plan(plan_id, approve)))


@app.command("call-service")
def call_service_command(
    domain: str = typer.Argument(...),
    service: str = typer.Argument(...),
    service_data: str | None = typer.Option(None, "--service-data", help="JSON service data."),
    target: str | None = typer.Option(None, "--target", help="JSON target object."),
    return_response: bool = typer.Option(False, help="Request a service response over WebSocket."),
) -> None:
    """Call an allowlisted Home Assistant service."""
    toolkit = HomeAssistantAgentToolkit()
    _print(
        asyncio.run(
            toolkit.call_service_safe(
                domain=domain,
                service=service,
                service_data=_parse_json(service_data),
                target=_parse_json(target),
                return_response=return_response,
            )
        )
    )


@app.command("automation-draft")
def automation_draft_command(
    title: str = typer.Argument(...),
    intent: str = typer.Argument(...),
    triggers: str | None = typer.Option(None, help="JSON array of trigger objects."),
    conditions: str | None = typer.Option(None, help="JSON array of condition objects."),
    actions: str | None = typer.Option(None, help="JSON array of action objects."),
    mode: str = typer.Option("single", help="Automation mode."),
) -> None:
    """Generate a review-first automation draft."""
    toolkit = HomeAssistantAgentToolkit()
    _print(
        toolkit.create_automation_draft(
            title=title,
            intent=intent,
            triggers=_parse_json(triggers),
            conditions=_parse_json(conditions),
            actions=_parse_json(actions),
            mode=mode,
        )
    )


@app.command("blueprint-draft")
def blueprint_draft_command(
    title: str = typer.Argument(...),
    intent: str = typer.Argument(...),
    inputs: str | None = typer.Option(None, help="JSON object of blueprint inputs."),
    triggers: str | None = typer.Option(None, help="JSON array of trigger objects."),
    conditions: str | None = typer.Option(None, help="JSON array of condition objects."),
    actions: str | None = typer.Option(None, help="JSON array of action objects."),
    mode: str = typer.Option("single", help="Automation mode."),
    author: str | None = typer.Option(None, help="Blueprint author."),
    source_url: str | None = typer.Option(None, help="Blueprint source URL."),
    min_version: str | None = typer.Option(None, help="Minimum Home Assistant version."),
    variables: str | None = typer.Option(None, help="JSON object of blueprint variables."),
) -> None:
    """Generate a Home Assistant blueprint draft."""
    toolkit = HomeAssistantAgentToolkit()
    _print(
        toolkit.create_blueprint_draft(
            title=title,
            intent=intent,
            inputs=_parse_json(inputs),
            triggers=_parse_json(triggers),
            conditions=_parse_json(conditions),
            actions=_parse_json(actions),
            mode=mode,
            author=author,
            source_url=source_url,
            min_version=min_version,
            variables=_parse_json(variables),
        )
    )


@app.command("save-blueprint")
def save_blueprint_command(
    title: str = typer.Argument(...),
    intent: str = typer.Argument(...),
    inputs: str | None = typer.Option(None, help="JSON object of blueprint inputs."),
    triggers: str | None = typer.Option(None, help="JSON array of trigger objects."),
    conditions: str | None = typer.Option(None, help="JSON array of condition objects."),
    actions: str | None = typer.Option(None, help="JSON array of action objects."),
    mode: str = typer.Option("single", help="Automation mode."),
    author: str | None = typer.Option(None, help="Blueprint author."),
    source_url: str | None = typer.Option(None, help="Blueprint source URL."),
    min_version: str | None = typer.Option(None, help="Minimum Home Assistant version."),
    variables: str | None = typer.Option(None, help="JSON object of blueprint variables."),
    relative_path: str | None = typer.Option(None, help="Relative path to save the blueprint YAML file."),
    overwrite: bool = typer.Option(False, help="Overwrite an existing file if present."),
) -> None:
    """Save a Home Assistant blueprint file into the workspace."""
    toolkit = HomeAssistantAgentToolkit()
    _print(
        toolkit.save_blueprint(
            title=title,
            intent=intent,
            inputs=_parse_json(inputs),
            triggers=_parse_json(triggers),
            conditions=_parse_json(conditions),
            actions=_parse_json(actions),
            mode=mode,
            author=author,
            source_url=source_url,
            min_version=min_version,
            variables=_parse_json(variables),
            relative_path=relative_path,
            overwrite=overwrite,
        )
    )


@app.command("validate-automation")
def validate_automation_command(
    title: str = typer.Argument(...),
    intent: str = typer.Argument(...),
    triggers: str | None = typer.Option(None, help="JSON array of trigger objects."),
    conditions: str | None = typer.Option(None, help="JSON array of condition objects."),
    actions: str | None = typer.Option(None, help="JSON array of action objects."),
    mode: str = typer.Option("single", help="Automation mode."),
) -> None:
    """Validate an automation against the current Home Assistant backend."""
    toolkit = HomeAssistantAgentToolkit()
    _print(
        asyncio.run(
            toolkit.validate_automation_config(
                title=title,
                intent=intent,
                triggers=_parse_json(triggers),
                conditions=_parse_json(conditions),
                actions=_parse_json(actions),
                mode=mode,
            )
        )
    )


@app.command("save-automation")
def save_automation_command(
    title: str = typer.Argument(...),
    intent: str = typer.Argument(...),
    triggers: str | None = typer.Option(None, help="JSON array of trigger objects."),
    conditions: str | None = typer.Option(None, help="JSON array of condition objects."),
    actions: str | None = typer.Option(None, help="JSON array of action objects."),
    mode: str = typer.Option("single", help="Automation mode."),
    automation_id: str | None = typer.Option(None, help="Home Assistant internal automation ID to update."),
    entity_id: str | None = typer.Option(None, help="Automation entity_id to update."),
) -> None:
    """Create or update an automation directly through the Home Assistant API."""
    toolkit = HomeAssistantAgentToolkit()
    _print(
        asyncio.run(
            toolkit.save_automation(
                title=title,
                intent=intent,
                triggers=_parse_json(triggers),
                conditions=_parse_json(conditions),
                actions=_parse_json(actions),
                mode=mode,
                automation_id=automation_id,
                entity_id=entity_id,
            )
        )
    )


@app.command("list-automation-traces")
def list_automation_traces_command(
    automation_id: str | None = typer.Option(None, help="Home Assistant internal automation ID."),
    entity_id: str | None = typer.Option(None, help="Automation entity_id."),
) -> None:
    """List recorded traces for an automation."""
    toolkit = HomeAssistantAgentToolkit()
    _print(
        asyncio.run(
            toolkit.list_automation_traces(
                automation_id=automation_id,
                entity_id=entity_id,
            )
        )
    )


@app.command("inspect-automation-trace")
def inspect_automation_trace_command(
    automation_id: str | None = typer.Option(None, help="Home Assistant internal automation ID."),
    entity_id: str | None = typer.Option(None, help="Automation entity_id."),
    run_id: str | None = typer.Option(None, help="Specific trace run_id. Defaults to the newest trace."),
) -> None:
    """Fetch and analyze one automation trace."""
    toolkit = HomeAssistantAgentToolkit()
    _print(
        asyncio.run(
            toolkit.inspect_automation_trace(
                automation_id=automation_id,
                entity_id=entity_id,
                run_id=run_id,
            )
        )
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
