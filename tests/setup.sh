#!/usr/bin/env bash
# =============================================================================
# Install the AI code-generation governance framework into a project.
# Platforms: Claude Code (CLI and VS Code extension) and GitHub Copilot (VS Code).
#
#   ./setup.sh /path/to/project                    both platforms
#   ./setup.sh /path/to/project --platform claude  Claude Code only
#   ./setup.sh /path/to/project --platform copilot GitHub Copilot only
#   ./setup.sh /path/to/project --dry-run          show what would happen
#   ./setup.sh --check [--platform ...]            check prerequisites on this machine only
#
# The script never overwrites a file. When a file exists, it writes
# <file>.governance-new next to it, so a person can merge the two.
# It does not change user settings, managed settings or repository settings.
# =============================================================================
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="" PLATFORM="both" CHECK_ONLY=0 DRY_RUN=0

usage() { sed -n '5,10p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --platform) PLATFORM="${2:-}"; shift 2 ;;
    --check)    CHECK_ONLY=1; shift ;;
    --dry-run)  DRY_RUN=1; shift ;;
    -h|--help)  usage 0 ;;
    -*)         echo "Unknown option: $1" >&2; usage 2 ;;
    *)          TARGET="$1"; shift ;;
  esac
done
case "$PLATFORM" in both|claude|copilot) ;; *) echo "--platform must be both, claude or copilot" >&2; exit 2 ;; esac
[ "$CHECK_ONLY" = 1 ] || [ -n "$TARGET" ] || usage 2

OK=0 WARN=0 FAIL=0
ok()   { printf '  [ok]   %s\n' "$1"; OK=$((OK+1)); }
warn() { printf '  [warn] %s\n' "$1"; WARN=$((WARN+1)); }
fail() { printf '  [fail] %s\n' "$1"; FAIL=$((FAIL+1)); }
has()  { command -v "$1" >/dev/null 2>&1; }
want() { [ "$PLATFORM" = both ] || [ "$PLATFORM" = "$1" ]; }

# ------------------------------------------------------------------ prerequisites
check_prerequisites() {
  local os; os="$(uname -s)"
  local wsl=0; grep -qi microsoft /proc/version 2>/dev/null && wsl=1
  echo "Prerequisites ($os$([ $wsl = 1 ] && echo ', WSL2'))"
  has git && ok "git $(git --version | awk '{print $3}')" || fail "git is missing"
  if has python3 && python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
    ok "python3 $(python3 -c 'import platform; print(platform.python_version())') (skill scanners, hooks)"
  else
    fail "python3 3.10 or later is missing. The skill scanners and the Claude Code hooks need it."
  fi
  has gh && ok "gh (optional: applies the ruleset)" || warn "gh is missing (optional). Apply the ruleset in the GitHub web UI."

  if want claude; then
    echo "Claude Code"
    if has claude; then ok "claude $(claude --version 2>/dev/null | head -1)"; else warn "claude CLI is missing. Install Claude Code, then run 'claude' in the project."; fi
    case "$os" in
      Darwin) ok "macOS: the sandbox uses Seatbelt (built in)" ;;
      Linux)
        has bwrap  && ok "bubblewrap (sandbox)" || fail "bubblewrap is missing. The sandbox cannot start (failIfUnavailable: true). Install: sudo apt install bubblewrap"
        has socat  && ok "socat (sandbox network proxy)" || fail "socat is missing. Install: sudo apt install socat" ;;
      *) fail "Native Windows has no Claude Code sandbox. Use WSL2." ;;
    esac
  fi

  if want copilot; then
    echo "GitHub Copilot in VS Code"
    if has code; then
      ok "VS Code $(code --version 2>/dev/null | head -1)"
      if code --list-extensions 2>/dev/null | grep -qi '^github\.copilot-chat$'; then ok "GitHub Copilot Chat extension"
      else warn "GitHub Copilot Chat extension not found. Install it and sign in with the organisation account."; fi
    else
      warn "VS Code 'code' command not found. Check VS Code and the Copilot Chat extension by hand."
    fi
    if [ "$os" = Linux ]; then
      local missing=""
      for t in bwrap slirp4netns unshare iptables; do has "$t" || missing="$missing $t"; done
      [ -z "$missing" ] && ok "agent sandbox dependencies (preview)" \
        || warn "Copilot agent sandbox (preview) needs:$missing. Install: sudo apt install bubblewrap slirp4netns util-linux iptables"
    fi
  fi
  echo "Result: $OK ok, $WARN warning(s), $FAIL failure(s)"
}

# ------------------------------------------------------------------ install
COMMON=(
  AGENTS.md
  governance/policy.md governance/risk-and-capability.md governance/controls.md
  governance/data-handling.md governance/approved-tools.yaml governance/exception-template.md
  specs/_template/spec.md specs/_template/plan.md
  policy-config
  scripts/check_metadata.py scripts/check_guardrails.py scripts/check_agent_config.py
  scripts/spec_lib.py scripts/evidence_summary.py scripts/reminders.py
  .github/workflows/governance.yml .github/workflows/governance-reminders.yml
  .github/pull_request_template.md .github/CODEOWNERS .github/ruleset.json
  .claude/skills .claude/agents
  docs/review-checklist.md docs/evidence-format.md
  agent/README.md
)
CLAUDE_ONLY=(CLAUDE.md .claude/settings.json .claude/hooks agent/profiles)
COPILOT_ONLY=(.vscode/settings.json)
CREATED=() SIDE_BY_SIDE=()

copy_file() {   # $1 = path relative to SRC
  local rel="$1" dst="$TARGET/$1"
  case "$rel" in *__pycache__*|*.pyc) return ;; esac
  if [ -e "$dst" ]; then
    cmp -s "$SRC/$rel" "$dst" && return
    dst="$dst.governance-new"; SIDE_BY_SIDE+=("$rel")
  else
    CREATED+=("$rel")
  fi
  [ "$DRY_RUN" = 1 ] && return
  mkdir -p "$(dirname "$dst")" && cp -p "$SRC/$rel" "$dst"
}

copy_item() {
  if [ -d "$SRC/$1" ]; then
    while IFS= read -r f; do copy_file "${f#"$SRC"/}"; done < <(find "$SRC/$1" -type f | sort)
  else
    copy_file "$1"
  fi
}

adapt_target() {   # changes that only make sense in a target project
  [ "$DRY_RUN" = 1 ] && return
  local wf="$TARGET/.github/workflows/governance.yml"
  [ -f "$wf.governance-new" ] && wf="$wf.governance-new"
  sed -i.bak 's/^  DEPENDENCY_SCAN_PATH: "sample-app"/  DEPENDENCY_SCAN_PATH: "."/' "$wf" && rm -f "$wf.bak"

  if [ "$PLATFORM" != both ]; then   # keep only the baseline section for the installed platform
    local base="$TARGET/policy-config/agent-baseline.yaml"
    [ -f "$base.governance-new" ] && base="$base.governance-new"
    python3 - "$base" "$PLATFORM" <<'PY'
import re, sys
path, platform = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()
drop = "vscode" if platform == "claude" else "claude_code"
text = re.sub(rf"^{drop}:\n(?:(?:  .*)?\n)*", "", text, flags=re.M)
open(path, "w", encoding="utf-8").write(text)
PY
  fi

  mkdir -p "$TARGET/governance/exceptions" && touch "$TARGET/governance/exceptions/.gitkeep"
  local gi="$TARGET/.gitignore"
  grep -qxF '.active-spec' "$gi" 2>/dev/null || printf '\n# governance framework: active specification for the scope hook\n.active-spec\n' >> "$gi"
  grep -qxF '__pycache__/' "$gi" 2>/dev/null || printf '__pycache__/\n' >> "$gi"
}

install() {
  [ -d "$TARGET" ] || { echo "Target folder '$TARGET' does not exist." >&2; exit 2; }
  TARGET="$(cd "$TARGET" && pwd)"
  [ "$TARGET" = "$SRC" ] && { echo "Target is the framework repository itself." >&2; exit 2; }
  git -C "$TARGET" rev-parse --is-inside-work-tree >/dev/null 2>&1 || warn "Target is not a git repository. CI and the guardrails need git."

  echo "Installing into $TARGET (platform: $PLATFORM$([ "$DRY_RUN" = 1 ] && echo ', dry run'))"
  for i in "${COMMON[@]}"; do copy_item "$i"; done
  want claude  && for i in "${CLAUDE_ONLY[@]}";  do copy_item "$i"; done
  want copilot && for i in "${COPILOT_ONLY[@]}"; do copy_item "$i"; done
  adapt_target
  [ "$DRY_RUN" = 1 ] || find "$TARGET/.claude" -name '*.py' -exec chmod +x {} + 2>/dev/null || true

  echo "  ${#CREATED[@]} file(s) $([ "$DRY_RUN" = 1 ] && echo 'would be created' || echo created)."
  if [ "${#SIDE_BY_SIDE[@]}" -gt 0 ]; then
    echo "  ${#SIDE_BY_SIDE[@]} file(s) exist already. The new version is next to each one as *.governance-new. Merge by hand:"
    printf '    %s\n' "${SIDE_BY_SIDE[@]}"
  fi
}

next_steps() {
  cat <<EOF

Next steps (a person does these once):
  1. Replace the placeholder accounts in .github/CODEOWNERS and 'owner' in governance/approved-tools.yaml.
  2. Check max_data_class and provider_terms_reviewed in governance/approved-tools.yaml against your contract.
  3. Add risky paths of your project to policy-config/risk-paths.yaml (auth, payments, migrations, infra).
  4. Add your build and test steps to the "Tests and SAST" job (.github/workflows/governance.yml, "PROJECT TESTS").
  5. Commit on a branch and open a pull request. Then apply the ruleset:
       gh api repos/OWNER/REPO/rulesets --method POST --input .github/ruleset.json
EOF
  want claude && cat <<EOF
  Claude Code:
  6. Run 'claude' in the project. Run /sandbox to check the sandbox. The session starts in plan mode.
  7. For a P1 or P2 change: claude --settings agent/profiles/claude-code-P1-edit.json (or P2-execute).
EOF
  want copilot && cat <<EOF
  GitHub Copilot:
  8. Open the project in VS Code. Use Copilot agent mode. Check that /new-change is offered.
  9. Copilot cloud agent: repository Settings > Copilot > Internet access: firewall on, recommended allowlist.
 10. Business or Enterprise organisation: set content exclusion and block suggestions that match public code
     (agent/README.md, section 6).
EOF
  cat <<EOF

Daily use: type '/new-change <what you want>' in the agent chat. Approve the specification, approve the plan,
review the pull request. Everything else runs in the agent and in CI.
EOF
}

check_prerequisites
[ "$CHECK_ONLY" = 1 ] && exit $((FAIL > 0))
echo
install
next_steps
