<#
.SYNOPSIS
  Install the AI code-generation governance framework into a project (Windows).

.DESCRIPTION
  Platforms: Claude Code and GitHub Copilot in VS Code.
  Native Windows has no Claude Code sandbox. For Claude Code, use WSL2 and setup.sh.
  The script never overwrites a file. When a file exists, it writes
  <file>.governance-new next to it, so a person can merge the two.
  It does not change user settings, managed settings or repository settings.

.EXAMPLE
  .\setup.ps1 -Target C:\src\project
  .\setup.ps1 -Target C:\src\project -Platform copilot
  .\setup.ps1 -Target C:\src\project -DryRun
  .\setup.ps1 -Check
#>
[CmdletBinding()]
param(
  [string]$Target,
  [ValidateSet('both', 'claude', 'copilot')][string]$Platform = 'both',
  [switch]$Check,
  [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
$Src = $PSScriptRoot
if (-not $Check -and -not $Target) { Get-Help $PSCommandPath -Examples; exit 2 }

$script:Ok = 0; $script:Warn = 0; $script:Fail = 0
function Ok($m)   { Write-Host "  [ok]   $m"; $script:Ok++ }
function Warn($m) { Write-Host "  [warn] $m" -ForegroundColor Yellow; $script:Warn++ }
function Fail($m) { Write-Host "  [fail] $m" -ForegroundColor Red; $script:Fail++ }
function Has($c)  { [bool](Get-Command $c -ErrorAction SilentlyContinue) }
function Want($p) { $Platform -eq 'both' -or $Platform -eq $p }

# ------------------------------------------------------------------ prerequisites
function Test-Prerequisites {
  Write-Host 'Prerequisites (Windows)'
  if (Has git) { Ok "git $((git --version) -replace 'git version ', '')" } else { Fail 'git is missing' }
  $py = @('python', 'py') | Where-Object { Has $_ } | Select-Object -First 1
  if ($py) {
    & $py -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>$null
    if ($LASTEXITCODE -eq 0) { Ok "$py 3.10 or later (skill scanners)" }
    else { Fail 'Python 3.10 or later is missing. The skill scanners need it.' }
  } else { Fail 'Python is missing. The skill scanners need Python 3.10 or later.' }
  if (Has gh) { Ok 'gh (optional: applies the ruleset)' } else { Warn 'gh is missing (optional). Apply the ruleset in the GitHub web UI.' }

  if (Want 'claude') {
    Write-Host 'Claude Code'
    if (Has claude) { Ok "claude $(claude --version 2>$null | Select-Object -First 1)" }
    else { Warn 'claude CLI is missing on Windows.' }
    Fail 'Native Windows has no Claude Code sandbox (failIfUnavailable: true stops the start). Run Claude Code in WSL2 and use setup.sh there.'
  }
  if (Want 'copilot') {
    Write-Host 'GitHub Copilot in VS Code'
    if (Has code) {
      Ok "VS Code $(code --version 2>$null | Select-Object -First 1)"
      if ((code --list-extensions 2>$null) -contains 'GitHub.copilot-chat') { Ok 'GitHub Copilot Chat extension' }
      else { Warn 'GitHub Copilot Chat extension not found. Install it and sign in with the organisation account.' }
    } else { Warn "VS Code 'code' command not found. Check VS Code and the Copilot Chat extension by hand." }
    Warn 'The VS Code agent sandbox on native Windows is experimental. Terminal approval rules still apply.'
  }
  Write-Host "Result: $script:Ok ok, $script:Warn warning(s), $script:Fail failure(s)"
}

# ------------------------------------------------------------------ install
$Common = @(
  'AGENTS.md',
  'governance/policy.md', 'governance/risk-and-capability.md', 'governance/controls.md',
  'governance/data-handling.md', 'governance/approved-tools.yaml', 'governance/exception-template.md',
  'specs/_template/spec.md', 'specs/_template/plan.md',
  'policy-config',
  'scripts/check_metadata.py', 'scripts/check_guardrails.py', 'scripts/check_agent_config.py',
  'scripts/spec_lib.py', 'scripts/evidence_summary.py', 'scripts/reminders.py',
  '.github/workflows/governance.yml', '.github/workflows/governance-reminders.yml',
  '.github/pull_request_template.md', '.github/CODEOWNERS', '.github/ruleset.json',
  '.claude/skills', '.claude/agents',
  'docs/review-checklist.md', 'docs/evidence-format.md',
  'agent/README.md'
)
$ClaudeOnly  = @('CLAUDE.md', '.claude/settings.json', '.claude/hooks', 'agent/profiles')
$CopilotOnly = @('.vscode/settings.json')
$Created = [System.Collections.Generic.List[string]]::new()
$SideBySide = [System.Collections.Generic.List[string]]::new()

function Copy-One([string]$Rel) {
  if ($Rel -match '__pycache__|\.pyc$') { return }
  $from = Join-Path $Src $Rel
  $dst = Join-Path $Target $Rel
  if (Test-Path $dst) {
    if ((Get-FileHash $from).Hash -eq (Get-FileHash $dst).Hash) { return }
    $dst = "$dst.governance-new"; $SideBySide.Add($Rel)
  } else { $Created.Add($Rel) }
  if ($DryRun) { return }
  New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
  Copy-Item -LiteralPath $from -Destination $dst
}

function Copy-Item-Tree([string]$Rel) {
  $path = Join-Path $Src $Rel
  if (Test-Path $path -PathType Container) {
    Get-ChildItem -LiteralPath $path -Recurse -File -Force | Sort-Object FullName | ForEach-Object {
      Copy-One ($_.FullName.Substring($Src.Length + 1) -replace '\\', '/')
    }
  } else { Copy-One $Rel }
}

function Resolve-Written([string]$Rel) {
  $p = Join-Path $Target $Rel
  if (Test-Path "$p.governance-new") { return "$p.governance-new" }
  return $p
}

function Update-Target {
  if ($DryRun) { return }
  $wf = Resolve-Written '.github/workflows/governance.yml'
  (Get-Content -Raw $wf) -replace '(?m)^  DEPENDENCY_SCAN_PATH: "sample-app"', '  DEPENDENCY_SCAN_PATH: "."' |
    Set-Content -NoNewline -Encoding utf8 $wf

  if ($Platform -ne 'both') {   # keep only the baseline section for the installed platform
    $base = Resolve-Written 'policy-config/agent-baseline.yaml'
    $drop = if ($Platform -eq 'claude') { 'vscode' } else { 'claude_code' }
    (Get-Content -Raw $base) -replace "(?m)^${drop}:\r?\n(?:(?:  .*)?\r?\n)*", '' |
      Set-Content -NoNewline -Encoding utf8 $base
  }

  $exc = Join-Path $Target 'governance/exceptions'
  New-Item -ItemType Directory -Force -Path $exc | Out-Null
  New-Item -ItemType File -Force -Path (Join-Path $exc '.gitkeep') | Out-Null

  $gi = Join-Path $Target '.gitignore'
  $lines = if (Test-Path $gi) { Get-Content $gi } else { @() }
  if ($lines -notcontains '.active-spec') {
    Add-Content $gi "`n# governance framework: active specification for the scope hook`n.active-spec"
  }
  if ($lines -notcontains '__pycache__/') { Add-Content $gi '__pycache__/' }
}

function Install-Framework {
  if (-not (Test-Path $Target -PathType Container)) { Write-Error "Target folder '$Target' does not exist."; exit 2 }
  $script:Target = (Resolve-Path $Target).Path
  if ($script:Target -eq $Src) { Write-Error 'Target is the framework repository itself.'; exit 2 }
  git -C $Target rev-parse --is-inside-work-tree 2>$null | Out-Null
  if ($LASTEXITCODE -ne 0) { Warn 'Target is not a git repository. CI and the guardrails need git.' }

  $mode = if ($DryRun) { ', dry run' } else { '' }
  Write-Host "Installing into $Target (platform: $Platform$mode)"
  $Common | ForEach-Object { Copy-Item-Tree $_ }
  if (Want 'claude')  { $ClaudeOnly  | ForEach-Object { Copy-Item-Tree $_ } }
  if (Want 'copilot') { $CopilotOnly | ForEach-Object { Copy-Item-Tree $_ } }
  Update-Target

  $verb = if ($DryRun) { 'would be created' } else { 'created' }
  Write-Host "  $($Created.Count) file(s) $verb."
  if ($SideBySide.Count -gt 0) {
    Write-Host "  $($SideBySide.Count) file(s) exist already. The new version is next to each one as *.governance-new. Merge by hand:"
    $SideBySide | ForEach-Object { Write-Host "    $_" }
  }
}

function Show-NextSteps {
  Write-Host @'

Next steps (a person does these once):
  1. Replace the placeholder accounts in .github/CODEOWNERS and 'owner' in governance/approved-tools.yaml.
  2. Check max_data_class and provider_terms_reviewed in governance/approved-tools.yaml against your contract.
  3. Add risky paths of your project to policy-config/risk-paths.yaml (auth, payments, migrations, infra).
  4. Add your build and test steps to the "Tests and SAST" job (.github/workflows/governance.yml, "PROJECT TESTS").
  5. Commit on a branch and open a pull request. Then apply the ruleset:
       gh api repos/OWNER/REPO/rulesets --method POST --input .github/ruleset.json
'@
  if (Want 'claude') { Write-Host @'
  Claude Code:
  6. Open the project in WSL2. Run 'claude', then /sandbox to check the sandbox. The session starts in plan mode.
  7. For a P1 or P2 change: claude --settings agent/profiles/claude-code-P1-edit.json (or P2-execute).
'@ }
  if (Want 'copilot') { Write-Host @'
  GitHub Copilot:
  8. Open the project in VS Code. Use Copilot agent mode. Check that /new-change is offered.
  9. Copilot cloud agent: repository Settings > Copilot > Internet access: firewall on, recommended allowlist.
 10. Business or Enterprise organisation: set content exclusion and block suggestions that match public code
     (agent/README.md, section 6).
'@ }
  Write-Host @'

Daily use: type '/new-change <what you want>' in the agent chat. Approve the specification, approve the plan,
review the pull request. Everything else runs in the agent and in CI.
'@
}

Test-Prerequisites
if ($Check) { if ($script:Fail -gt 0) { exit 1 } else { exit 0 } }
Write-Host ''
Install-Framework
Show-NextSteps
