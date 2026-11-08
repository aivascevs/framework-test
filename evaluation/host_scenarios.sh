#!/usr/bin/env bash
# =============================================================================
# Open one pull request per evaluation scenario on a TEST repository on GitHub.
# This shows what the host does with each check result: block, allow, or ask
# for review. The local runner (run_scenarios.py) cannot show that.
#
#   EVAL_REPO=owner/test-repo evaluation/host_scenarios.sh all
#   EVAL_REPO=owner/test-repo evaluation/host_scenarios.sh S04 S24
#   evaluation/host_scenarios.sh --local all     # make the branches only, no push, no PR
#   evaluation/host_scenarios.sh --list
#
# Safety:
#   - Use a disposable test repository with synthetic data only.
#   - EVAL_REPO must name the repository that 'gh' sees as origin, or the script stops.
#   - The script never merges. Close each pull request after you record the result.
# Needs: git, gh (logged in), a clean working tree on the base branch.
# =============================================================================
set -euo pipefail

BASE="${BASE:-main}"
FIX="evaluation/fixtures"
LOCAL=0
[ "${1:-}" = "--local" ] && { LOCAL=1; shift; }

declare -A TITLE=(
  [S01]="Conforming change"                         [S02]="PR without risk class and specification link"
  [S04]="Synthetic secret that matches a rule"      [S05]="Synthetic secret in a format no rule covers"
  [S06]="Seeded SQL injection covered by a rule"    [S07]="Missing authorisation check, no rule"
  [S08]="Dependency with a published advisory"      [S09]="Dependency licence outside the allowlist"
  [S11]="Pull request changes AGENTS.md"            [S15]="File outside the specification scope"
  [S16]="Changed path needs a higher risk class"    [S17]="Test removed and suppression added"
  [S18]="Agent configuration weakened"              [S19]="Personal data in an added test"
  [S24]="Over-budget pull request"                  [S25]="Over-budget pull request with an exception"
  [S26]="Large new file not declared as generated"
)
ORDER=(S01 S02 S04 S05 S06 S07 S08 S09 S11 S15 S16 S17 S18 S19 S24 S25 S26)

if [ "${1:-}" = "--list" ] || [ $# -eq 0 ]; then
  for s in "${ORDER[@]}"; do printf '%s  %s\n' "$s" "${TITLE[$s]}"; done
  echo
  echo "Manual on the host (no script): S03 (remove 'Governance metadata' from the required checks, then rerun S02),"
  echo "S10 (try to merge S01 without an approval). Agent scenarios: docs/TESTING.md, level 3."
  exit 0
fi
[ "$1" = "all" ] && set -- "${ORDER[@]}"

git diff --quiet && git diff --cached --quiet || { echo "The working tree is not clean." >&2; exit 2; }
[ "$(git rev-parse --abbrev-ref HEAD)" = "$BASE" ] || { echo "Check out '$BASE' first (or set BASE)." >&2; exit 2; }
if [ "$LOCAL" = 0 ]; then
  actual="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
  [ "${EVAL_REPO:-}" = "$actual" ] || {
    echo "Set EVAL_REPO=$actual to confirm that this is a disposable test repository." >&2; exit 2; }
fi

prepare() {   # apply the fixture of scenario $1 and print the PR body file
  case "$1" in
    S01) git apply "$FIX/S01-conforming-change.patch"; echo "$FIX/S01-pr-body.md" ;;
    S02) git apply "$FIX/S01-conforming-change.patch"; echo "$FIX/S02-pr-body-missing-fields.md" ;;
    S04) cp "$FIX/S04-synthetic-secret.py" sample-app/orders/settings.py; echo "$FIX/eval-pr-body.md" ;;
    S05) cp "$FIX/S05-unusual-secret-format.py" sample-app/orders/settings.py; echo "$FIX/eval-pr-body.md" ;;
    S06) git apply "$FIX/S06-seeded-sql-injection.patch"; echo "$FIX/eval-pr-body.md" ;;
    S07) git apply "$FIX/S07-missing-authorisation.patch"; echo "$FIX/eval-pr-body.md" ;;
    S08) cp "$FIX/S08-requirements-advisory.txt" sample-app/requirements.txt; echo "$FIX/eval-pr-body.md" ;;
    S09) cp "$FIX/S09-requirements-licence.txt" sample-app/requirements.txt; echo "$FIX/eval-pr-body.md" ;;
    S11) printf '\n<!-- S11: harmless one-line change for the code-owner check -->\n' >> AGENTS.md
         echo "$FIX/eval-pr-body.md" ;;
    S15) git apply "$FIX/S15-out-of-scope-file.patch"; echo "$FIX/S01-pr-body.md" ;;
    S16) git apply "$FIX/S16-risk-drift.patch"; echo "$FIX/S01-pr-body.md" ;;
    S17) git apply "$FIX/S17-test-removed-and-suppression.patch"; echo "$FIX/S01-pr-body.md" ;;
    S18) git apply "$FIX/S18-agent-config-weakened.patch"; echo "$FIX/S01-pr-body.md" ;;
    S19) git apply "$FIX/S19-personal-data-in-test.patch"; echo "$FIX/S01-pr-body.md" ;;
    S24) git apply "$FIX/S24-over-budget-change.patch"; echo "$FIX/S01-pr-body.md" ;;
    S25) git apply "$FIX/S24-over-budget-change.patch"
         mkdir -p governance/exceptions
         expiry="$(python3 -c 'import datetime as d; print(d.date.today() + d.timedelta(days=30))')"
         printf '# EXC-900 Over-budget reason table (evaluation scenario S25)\n\n| Field | Value |\n|---|---|\n| Approved by | Risk owner (synthetic) |\n| Expiry or review date | %s |\n' \
           "$expiry" > governance/exceptions/EXC-900-evaluation.md
         sed 's#^Exception: none#Exception: governance/exceptions/EXC-900-evaluation.md#' "$FIX/S01-pr-body.md" > .s25-body.md
         echo ".s25-body.md" ;;
    S26) git apply "$FIX/S26-large-new-file.patch"; echo "$FIX/S01-pr-body.md" ;;
    *) echo "Unknown scenario: $1" >&2; return 1 ;;
  esac
}

for sid in "$@"; do
  [ -n "${TITLE[$sid]:-}" ] || { echo "Unknown scenario: $sid (use --list)" >&2; exit 2; }
  branch="eval/$sid"
  git switch -q -c "$branch" "$BASE"
  body="$(prepare "$sid")"
  if [ "$body" = ".s25-body.md" ]; then tmp="$(mktemp)"; mv .s25-body.md "$tmp"; body="$tmp"; fi
  git add -A
  git -c user.name="${GIT_AUTHOR_NAME:-evaluation}" -c user.email="${GIT_AUTHOR_EMAIL:-evaluation@example.test}" \
    commit -q -m "[eval] $sid ${TITLE[$sid]}"
  if [ "$LOCAL" = 1 ]; then
    echo "$sid: branch $branch created (local only), PR body: $body"
  else
    git push -q -u origin "$branch"
    gh pr create --base "$BASE" --head "$branch" --title "[eval] $sid ${TITLE[$sid]}" --body-file "$body" >/dev/null
    echo "$sid: pull request opened on $branch"
  fi
  git switch -q "$BASE"
done

echo
echo "Wait for the checks. Then record each result in evaluation/results/ (copy results-template.md)."
echo "Close the pull requests without a merge:  gh pr list --search 'head:eval/' --json number --jq '.[].number' | xargs -n1 gh pr close"
