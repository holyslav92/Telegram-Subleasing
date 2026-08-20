#!/usr/bin/env python3
"""Cursor Task/subagentStart hook: keep Excalibur in one-window chain.

Reads hook JSON from stdin, prints permission JSON to stdout.
See docs/cursor/hooks-and-skills.md and shared/subagent-chain.md.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "shared/pipeline-model-policy.json"

ORCHESTRATOR_NAMES = frozenset(
    {
        "excalibur-blog-director",
        "excalibur-blog-setup",
    }
)

SPECIALIST_PREFIX = "excalibur-blog-"

BUILTIN_OK_DEFAULT = (
    "explore",
    "bash",
    "shell",
    "browser",
    "debug",
    "computerUse",
    "docs-researcher",
)


def load_policy() -> dict[str, Any]:
    try:
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def task_input(payload: dict[str, Any]) -> dict[str, Any]:
    tool_input = _as_dict(payload.get("tool_input"))
    if tool_input:
        return tool_input
    return _as_dict(payload)


def subagent_type_of(payload: dict[str, Any]) -> str:
    tool_input = task_input(payload)
    raw = (
        tool_input.get("subagent_type")
        or payload.get("subagent_type")
        or tool_input.get("name")
        or ""
    )
    return str(raw).strip()


def infer_speaker_agent(transcript: str) -> str | None:
    """Return agent YAML name if the current conversation looks like one."""
    if not transcript:
        return None
    head = transcript[:12000]
    for line in head.splitlines():
        stripped = line.strip()
        if stripped.startswith("name:"):
            name = stripped.split(":", 1)[1].strip().strip("\"'")
            if name.startswith(SPECIALIST_PREFIX):
                return name
    marker = "name: excalibur-blog-"
    idx = head.find(marker)
    if idx >= 0:
        rest = head[idx + len("name:") :].strip()
        return rest.split()[0].strip("\"',")
    return None


def read_transcript(payload: dict[str, Any]) -> str:
    path = payload.get("transcript_path")
    if not path:
        return ""
    try:
        return Path(str(path)).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def allow() -> dict[str, str]:
    return {"permission": "allow"}


def deny(message: str) -> dict[str, str]:
    return {
        "permission": "deny",
        "user_message": message,
        "agent_message": message,
    }


def speaker_is_specialist(payload: dict[str, Any]) -> bool:
    name = infer_speaker_agent(read_transcript(payload))
    if not name:
        return False
    return name not in ORCHESTRATOR_NAMES


def speaker_is_setup(payload: dict[str, Any]) -> bool:
    return infer_speaker_agent(read_transcript(payload)) == "excalibur-blog-setup"


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def decide_task(payload: dict[str, Any], policy: dict[str, Any]) -> dict[str, str]:
    tool_input = task_input(payload)
    kind = subagent_type_of(payload)
    never_as_task = set(policy.get("never_as_task") or list(ORCHESTRATOR_NAMES))
    forbidden_types = set(policy.get("forbidden_subagent_types") or ["best-of-n-runner"])
    setup_may = set(policy.get("setup_may_task") or [])
    builtin_ok = set(policy.get("builtin_subagents_allowed") or BUILTIN_OK_DEFAULT)

    environment = str(tool_input.get("environment") or "").strip().lower()
    if environment == "cloud":
        return deny(
            "Excalibur chain: не запускай cloud subagent (environment=cloud / "
            "/in-cloud). Шаг должен остаться foreground Task в этом окне. "
            "См. shared/subagent-chain.md."
        )

    if truthy(tool_input.get("run_in_background")) and kind.startswith(SPECIALIST_PREFIX):
        return deny(
            "Excalibur chain: пайплайн-субагент только foreground "
            "(run_in_background=false), иначе цепочка в одном окне рвётся."
        )

    if kind in forbidden_types:
        return deny(
            f"Excalibur chain: {kind} даёт isolated worktree/другое окно. "
            "Запрещено для статьи."
        )

    if kind in never_as_task:
        return deny(
            f"Excalibur chain: {kind} — оркестратор чата, не Task. "
            "Не вызывай Task(director) / Task(setup)."
        )

    if kind.startswith(SPECIALIST_PREFIX) and speaker_is_specialist(payload):
        if speaker_is_setup(payload) and kind in setup_may:
            return allow()
        return deny(
            f"Excalibur chain: специалист не запускает {kind}. "
            "Только Директор (или Setup → setup-voice/visual) вызывает "
            "Task(excalibur-blog-*). Не начинай свой пайплайн."
        )

    if kind and not kind.startswith(SPECIALIST_PREFIX) and kind not in builtin_ok:
        if speaker_is_specialist(payload) and kind in {
            "generalPurpose",
            "best-of-n-runner",
        }:
            return deny(
                f"Excalibur chain: специалисту нельзя Task({kind}) — "
                "это отдельный пайплайн."
            )

    return allow()


def decide_subagent_start(payload: dict[str, Any], policy: dict[str, Any]) -> dict[str, str]:
    kind = subagent_type_of(payload)
    never_as_task = set(policy.get("never_as_task") or list(ORCHESTRATOR_NAMES))
    forbidden_types = set(policy.get("forbidden_subagent_types") or ["best-of-n-runner"])
    if kind in never_as_task or kind in forbidden_types:
        return deny(
            f"Excalibur chain: subagentStart blocked for {kind or 'unknown'}."
        )
    if kind.startswith(SPECIALIST_PREFIX) and speaker_is_specialist(payload):
        setup_may = set(policy.get("setup_may_task") or [])
        if speaker_is_setup(payload) and kind in setup_may:
            return allow()
        return deny(
            f"Excalibur chain: nested {kind} from a specialist is forbidden."
        )
    return allow()


def decide(payload: dict[str, Any]) -> dict[str, str]:
    policy = load_policy()
    event = str(payload.get("hook_event_name") or "").strip()
    tool_name = str(payload.get("tool_name") or "").strip()
    if event == "subagentStart" or (
        not event and "subagent_type" in payload and "tool_name" not in payload
    ):
        return decide_subagent_start(payload, policy)
    if event == "preToolUse" or tool_name.lower() == "task":
        if tool_name and tool_name.lower() != "task":
            return allow()
        return decide_task(payload, policy)
    return allow()


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        json.dump(allow(), sys.stdout)
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        json.dump(allow(), sys.stdout)
        return 0
    if not isinstance(payload, dict):
        json.dump(allow(), sys.stdout)
        return 0
    json.dump(decide(payload), sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
