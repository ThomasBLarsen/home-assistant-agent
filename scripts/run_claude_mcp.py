"""Launch the Home Assistant MCP server without a console window.

Run with pythonw.exe (GUI subsystem) so Claude Desktop / Claude Code does not
pop up a console window for every conversation. Sets cwd to the workspace so
`.env` and `logs/` resolve correctly regardless of where the client spawns us.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent


def main() -> None:
    os.chdir(WORKSPACE)
    src = WORKSPACE / "src"
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from home_assistant_agent.mcp_server import main as run_server

    run_server()


if __name__ == "__main__":
    main()
