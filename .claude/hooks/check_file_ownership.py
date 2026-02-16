#!/usr/bin/env python3
"""
PreToolUse hook: validates file ownership before Edit/Write operations.

Reads the CLAUDE_TEAMMATE environment variable to determine which teammate
is running, then checks if the target file is within that teammate's
allowed paths. Exits with code 2 (block) if not allowed, 0 if allowed.

Usage in .claude/settings.local.json:
    "hooks": {
        "PreToolUse": [{
            "matcher": "Edit|Write",
            "hooks": [{
                "type": "command",
                "command": "python .claude/hooks/check_file_ownership.py \"$TOOL_INPUT\"",
                "timeout": 5
            }]
        }]
    }
"""

import json
import os
import sys

# Ownership map: teammate name -> list of allowed path prefixes
OWNERSHIP_MAP = {
    "architect": [
        "CLAUDE.md",
        "core/",
        ".claude/teammates/",
        "pyproject.toml",
        ".pre-commit-config.yaml",
        "conftest.py",
        "requirements.txt",
        "Dockerfile",
        "docker-compose.yml",
        "Makefile",
    ],
    "crm-developer": [
        "apps/crm/",
    ],
    "contacts-developer": [
        "apps/contacts/",
    ],
    "calls-developer": [
        "apps/calls/",
    ],
    "activities-developer": [
        "apps/activities/",
    ],
    "user-settings-developer": [
        "apps/user_settings/",
    ],
    "frontend-developer": [
        "templates/",
        "static/",
    ],
}


def get_file_path(tool_input_str):
    """Extract file_path from tool input JSON."""
    try:
        data = json.loads(tool_input_str)
        return data.get("file_path", "")
    except (json.JSONDecodeError, TypeError):
        return ""


def normalize_path(file_path, project_root):
    """Convert absolute path to project-relative path."""
    abs_path = os.path.abspath(file_path)
    abs_root = os.path.abspath(project_root)
    if abs_path.startswith(abs_root):
        rel = os.path.relpath(abs_path, abs_root)
        return rel
    return file_path


def check_ownership(teammate, rel_path):
    """Check if the teammate is allowed to modify the given path."""
    if teammate not in OWNERSHIP_MAP:
        # Unknown teammate — allow (might be running without teammate context)
        return True

    allowed_paths = OWNERSHIP_MAP[teammate]
    for allowed in allowed_paths:
        if rel_path == allowed or rel_path.startswith(allowed):
            return True

    return False


def main():
    teammate = os.environ.get("CLAUDE_TEAMMATE", "").strip().lower()

    # If no teammate is set, allow all operations (solo mode)
    if not teammate:
        sys.exit(0)

    tool_input = sys.argv[1] if len(sys.argv) > 1 else ""
    file_path = get_file_path(tool_input)

    if not file_path:
        # No file path found — allow (might be a non-file operation)
        sys.exit(0)

    # Determine project root (two levels up from this script)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    rel_path = normalize_path(file_path, project_root)

    if check_ownership(teammate, rel_path):
        sys.exit(0)
    else:
        print(
            f"BLOCKED: Teammate '{teammate}' is not allowed to modify '{rel_path}'. "
            f"Allowed paths: {OWNERSHIP_MAP.get(teammate, [])}"
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
