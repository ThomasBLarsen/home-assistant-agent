from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .tools import HomeAssistantAgentToolkit

mcp = FastMCP(
    "Home Assistant Agent",
    instructions=(
        "Use preview tools before apply tools. Do not call apply_change_plan unless the user "
        "has reviewed the plan and provided the approval code."
    ),
    json_response=True,
)

toolkit = HomeAssistantAgentToolkit()


@mcp.tool()
async def scan_home_assistant() -> dict[str, Any]:
    """Build a Home Assistant inventory snapshot and summarize automations."""
    return await toolkit.scan_home_assistant()


@mcp.tool()
async def list_entities(
    domain: str | None = None,
    area_id: str | None = None,
    state: str | None = None,
) -> dict[str, Any]:
    """List Home Assistant entities with optional filters."""
    return await toolkit.list_entities(domain=domain, area_id=area_id, state=state)


@mcp.tool()
async def find_issues() -> dict[str, Any]:
    """Run diagnostics for unhealthy entities and automation drift."""
    return await toolkit.find_issues()


@mcp.tool()
async def preview_entity_cleanup() -> dict[str, Any]:
    """Prepare a guarded entity cleanup plan and return an approval code."""
    return await toolkit.preview_entity_cleanup()


@mcp.tool()
async def preview_automation_cleanup() -> dict[str, Any]:
    """Prepare a guarded automation cleanup plan and return an approval code."""
    return await toolkit.preview_automation_cleanup()


@mcp.tool()
def create_automation_draft(
    title: str,
    intent: str,
    triggers: list[dict[str, Any]] | None = None,
    conditions: list[dict[str, Any]] | None = None,
    actions: list[dict[str, Any]] | None = None,
    mode: str = "single",
) -> dict[str, Any]:
    """Generate a review-first automation draft as YAML and JSON."""
    return toolkit.create_automation_draft(
        title=title,
        intent=intent,
        triggers=triggers,
        conditions=conditions,
        actions=actions,
        mode=mode,
    )


@mcp.tool()
def create_blueprint_draft(
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
    """Generate a Home Assistant automation blueprint as YAML and JSON."""
    return toolkit.create_blueprint_draft(
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


@mcp.tool()
def save_blueprint(
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
    """Save a Home Assistant automation blueprint YAML file into the workspace."""
    return toolkit.save_blueprint(
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
        relative_path=relative_path,
        overwrite=overwrite,
    )


@mcp.tool()
async def validate_automation_config(
    title: str,
    intent: str,
    triggers: list[dict[str, Any]] | None = None,
    conditions: list[dict[str, Any]] | None = None,
    actions: list[dict[str, Any]] | None = None,
    mode: str = "single",
) -> dict[str, Any]:
    """Validate an automation config against the Home Assistant backend without saving it."""
    return await toolkit.validate_automation_config(
        title=title,
        intent=intent,
        triggers=triggers,
        conditions=conditions,
        actions=actions,
        mode=mode,
    )


@mcp.tool()
async def save_automation(
    title: str,
    intent: str,
    triggers: list[dict[str, Any]] | None = None,
    conditions: list[dict[str, Any]] | None = None,
    actions: list[dict[str, Any]] | None = None,
    mode: str = "single",
    automation_id: str | None = None,
    entity_id: str | None = None,
) -> dict[str, Any]:
    """Create a new automation or update an existing one directly through the Home Assistant API."""
    return await toolkit.save_automation(
        title=title,
        intent=intent,
        triggers=triggers,
        conditions=conditions,
        actions=actions,
        mode=mode,
        automation_id=automation_id,
        entity_id=entity_id,
    )


@mcp.tool()
async def list_automation_traces(
    automation_id: str | None = None,
    entity_id: str | None = None,
) -> dict[str, Any]:
    """List recorded traces for an automation by internal automation ID or entity_id."""
    return await toolkit.list_automation_traces(
        automation_id=automation_id,
        entity_id=entity_id,
    )


@mcp.tool()
async def inspect_automation_trace(
    automation_id: str | None = None,
    entity_id: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Fetch and analyze one automation trace, including common root-cause hints."""
    return await toolkit.inspect_automation_trace(
        automation_id=automation_id,
        entity_id=entity_id,
        run_id=run_id,
    )


@mcp.tool()
async def apply_change_plan(plan_id: str, approval_code: str) -> dict[str, Any]:
    """Apply a saved change plan after the user confirms it with the approval code."""
    return await toolkit.apply_change_plan(plan_id, approval_code)


@mcp.tool()
async def call_service_safe(
    domain: str,
    service: str,
    service_data: dict[str, Any] | None = None,
    target: dict[str, Any] | None = None,
    return_response: bool = False,
) -> dict[str, Any]:
    """Call a Home Assistant service only if its domain is allowlisted."""
    return await toolkit.call_service_safe(
        domain=domain,
        service=service,
        service_data=service_data,
        target=target,
        return_response=return_response,
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
