#!/usr/bin/env python3
"""UserPromptSubmit hook (Claude Code CLI): stop a prompt that contains a secret or personal data (C3, A4).

Uses the same patterns as the sensitive-data-guard skill. When a pattern matches,
the hook blocks the prompt before the model sees it and tells the user the KIND
of finding. It never prints the value.

Limits: the hook runs in the Claude Code CLI only. The VS Code extension and
GitHub Copilot chat do not run it (see agent/README.md). Patterns find only the
formats they describe. A text marked "sensitive-data: synthetic" is not blocked.

Exit codes (Claude Code hook protocol): 0 permit, 2 block (stderr goes to the user).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "sensitive-data-guard" / "scripts"))


def main() -> int:
    try:
        event = json.load(sys.stdin)
        from scan_sensitive import SYNTHETIC_MARKER, scan_text
    except Exception:  # never stop the user because the hook itself is broken
        return 0
    prompt = event.get("prompt") or ""
    if SYNTHETIC_MARKER in prompt:
        return 0
    findings = scan_text(prompt, "prompt")
    if not findings:
        return 0
    kinds = sorted({f"{f.kind} ({f.rule})" for f in findings})
    print("Prompt blocked by the sensitive-data guard: it looks like it contains "
          + ", ".join(kinds) + ". Remove the value, or replace it with a placeholder or a synthetic "
          "value, and send the prompt again. If the value is synthetic test data, add the words "
          "'sensitive-data: synthetic' to the prompt.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
