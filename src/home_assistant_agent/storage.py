from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ChangePlan


def _json_default(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default),
        encoding="utf-8",
    )


def append_jsonl(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=_json_default))
        handle.write("\n")


def save_change_plan(base_dir: Path, plan: ChangePlan) -> Path:
    path = base_dir / f"{plan.plan_id}.json"
    write_json(path, plan.to_dict())
    return path


def load_change_plan(base_dir: Path, plan_id: str) -> dict[str, Any]:
    path = base_dir / f"{plan_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Change plan '{plan_id}' does not exist.")
    return json.loads(path.read_text(encoding="utf-8"))
