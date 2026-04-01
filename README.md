# Home Assistant Agent Framework

This project provides a guarded Python framework for connecting an AI assistant to Home Assistant.

It includes:

- A Home Assistant client for REST and WebSocket access
- Inventory and diagnostics helpers for entities and automations
- Preview and approval-based change plans
- Direct automation validation and save helpers for storage-based automations
- Blueprint draft and file-save helpers for reusable automation templates
- Automation trace inspection helpers with root-cause hints for common failures
- A CLI for local operations
- An MCP server so AI clients can use structured tools safely

## Setup

1. Make sure `.env` contains your `HOME_ASSISTANT_URL` and `HOME_ASSISTANT_TOKEN`.
2. Run the one-time installer:

   ```powershell
   .\scripts\install_cursor_mcp.ps1
   ```

3. Reload Cursor if it was already open.
4. Check `Settings -> MCP` and confirm `home-assistant-agent` is enabled.

## Cursor MCP

This project now includes a ready-to-use project MCP config at `.cursor/mcp.json`.

Cursor launches the server through `scripts/run_cursor_mcp.ps1`, which:

- uses the local `.venv`
- installs the package automatically if needed
- loads secrets from `.env`
- starts the MCP server over `stdio`

Once Cursor sees the project MCP config, the tools should become available automatically in chat.

## CLI

You can also use the framework directly from the terminal:

- Run a scan:
 
  ```powershell
  .\.venv\Scripts\home-assistant-agent scan
  ```

- Validate an automation config against Home Assistant before saving it:

  ```powershell
  .\.venv\Scripts\home-assistant-agent validate-automation "Leak alert" "Warn on water leak" --triggers "[{\"trigger\":\"state\",\"entity_id\":\"binary_sensor.leak\",\"to\":\"on\"}]" --actions "[{\"action\":\"notify.notify\",\"data\":{\"message\":\"Leak detected\"}}]"
  ```

- Save a new storage-based automation directly through the API:

  ```powershell
  .\.venv\Scripts\home-assistant-agent save-automation "Leak alert" "Warn on water leak" --triggers "[{\"trigger\":\"state\",\"entity_id\":\"binary_sensor.leak\",\"to\":\"on\"}]" --actions "[{\"action\":\"notify.notify\",\"data\":{\"message\":\"Leak detected\"}}]"
  ```

- Generate a blueprint draft with `!input` references:

  ```powershell
  .\.venv\Scripts\home-assistant-agent blueprint-draft "Motion alert" "Announce on motion" --inputs "{\"motion_sensor\":{\"name\":\"Motion Sensor\",\"selector\":{\"entity\":{\"filter\":[{\"domain\":\"binary_sensor\",\"device_class\":\"motion\"}]}}}}" --triggers "[{\"trigger\":\"state\",\"entity_id\":\"!input motion_sensor\",\"to\":\"on\"}]" --actions "[{\"action\":\"notify.notify\",\"data\":{\"message\":\"Motion detected\"}}]"
  ```

- Save a blueprint file into the workspace:

  ```powershell
  .\.venv\Scripts\home-assistant-agent save-blueprint "Motion alert" "Announce on motion" --inputs "{\"motion_sensor\":{\"name\":\"Motion Sensor\",\"selector\":{\"entity\":{\"filter\":[{\"domain\":\"binary_sensor\",\"device_class\":\"motion\"}]}}}}" --triggers "[{\"trigger\":\"state\",\"entity_id\":\"!input motion_sensor\",\"to\":\"on\"}]" --actions "[{\"action\":\"notify.notify\",\"data\":{\"message\":\"Motion detected\"}}]" --author "Larsen"
  ```

- Inspect the latest trace for an automation and get a root-cause summary:

  ```powershell
  .\.venv\Scripts\home-assistant-agent inspect-automation-trace --entity-id automation.vannlekkasje_varsling
  ```

- Start the MCP server manually:

  ```powershell
  .\.venv\Scripts\home-assistant-agent-mcp
  ```
