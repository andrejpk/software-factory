<#
.SYNOPSIS
  Idempotently installs the Software Factory Copilot automations and labels into a repository.

.DESCRIPTION
  Reads automations/definitions/*.json, assembles each prompt from automations/prompts, and creates
  or updates the automation with the same name through the agent automations REST API
  (public preview, API version 2026-03-10). Also creates the sf:* labels.

  Uses the gh CLI and whichever account gh is authenticated as. Personal automations act as, and
  bill, that account. Run `gh api user --jq .login` first to confirm the identity.

  AI credit limits are sent as `run_limit` and `usage_limits`. These fields are not in the published
  REST reference; the API stores them in nano-credits (1 AI credit = 1e9), which this script handles.

.EXAMPLE
  ./automations/install.ps1 -Repo andrejpk/sf-automation-sandbox
  ./automations/install.ps1 -Repo andrejpk/sf-automation-sandbox -Disable
#>
param(
    [Parameter(Mandatory)] [string] $Repo,
    [switch] $Disable,
    [switch] $SkipLabels
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$api = "/agents/repos/$Repo/automations"
$hdr = @('-H', 'X-GitHub-Api-Version: 2026-03-10')
$nano = [int64]1000000000

function Invoke-Gh([string] $Method, [string] $Path, $Body) {
    $ghArgs = @('api') + $hdr + @('-X', $Method, $Path)
    if ($null -ne $Body) {
        $json = $Body | ConvertTo-Json -Depth 10
        $out = $json | gh @ghArgs --input - 2>&1
    } else {
        $out = gh @ghArgs 2>&1
    }
    if ($LASTEXITCODE -ne 0) { throw "gh api $Method $Path failed: $out" }
    return ($out | Out-String | ConvertFrom-Json)
}

Write-Host "Installing as $(gh api user --jq .login) into $Repo"

if (-not $SkipLabels) {
    $labels = @{
        'sf:brd' = '5319e7'; 'sf:plan' = '1d76db'; 'sf:planned' = 'c5def5'; 'sf:task' = '0e8a16'
        'sf:ready' = 'fbca04'; 'sf:in-progress' = 'd93f0b'; 'sf:in-review' = '0052cc'
        'sf:blocked' = 'b60205'; 'sf:done' = '2ea44f'; 'sf:status' = 'bfdadc'
        'sf:pr' = '6f42c1'; 'sf:review' = '0366d6'; 'sf:fix' = 'e99695'
                'sf:held-ci' = 'ff7619'
        'sf:triage' = 'f9d0c4'; 'sf:triaged' = 'fef2c0'; 'sf:backlog' = 'ededed'
        'sf:bug' = 'd73a4a'; 'sf:enhancement' = 'a2eeef'; 'sf:feature' = '7057ff'
        'sf:p1' = 'b60205'; 'sf:p2' = 'fbca04'; 'sf:p3' = 'c2e0c6'; 'sf:hold' = '000000'
        'sf:retry' = '0e8a16'; 'sf:ci-green' = '2ea44f'; 'sf:groom' = 'bfdadc'
        'sf:needs-design' = 'f7c6c7'; 'sf:design' = 'd4c5f9'
    }
    foreach ($name in $labels.Keys) {
        gh label create $name --color $labels[$name] --repo $Repo --force | Out-Null
    }
    Write-Host "Labels ensured: $($labels.Keys -join ', ')"
}

$existing = @{}
foreach ($a in (Invoke-Gh GET "$($api)?per_page=100" $null).automations) { $existing[$a.name] = $a }

$installed = @{}
# Definitions that chain on other automations (automation_names) install last, so their upstream IDs exist.
$files = Get-ChildItem "$root/definitions/*.json" | Sort-Object @{ e = { (Get-Content $_.FullName -Raw) -match 'automation_names' } }, Name
foreach ($file in $files) {
    $def = Get-Content $file.FullName -Raw | ConvertFrom-Json
    foreach ($t in $def.triggers.PSObject.Properties) {
        if ($t.Value.PSObject.Properties.Name -contains 'automation_names') {
            $ids = foreach ($n in $t.Value.automation_names) {
                $id = if ($installed.ContainsKey($n)) { $installed[$n] } elseif ($existing.ContainsKey($n)) { $existing[$n].id } else { throw "Unknown upstream automation '$n' in $($file.Name)" }
                $id
            }
            $t.Value.PSObject.Properties.Remove('automation_names')
            $t.Value | Add-Member -NotePropertyName automation_ids -NotePropertyValue @($ids)
        }
    }
    $prompt = ($def.prompt_files | ForEach-Object { Get-Content "$root/prompts/$_" -Raw }) -join "`n`n"
    if ($prompt.Length -gt 10000) { throw "$($def.name): prompt is $($prompt.Length) characters; the limit is 10,000" }
    $body = [ordered]@{
        name                           = $def.name
        prompt                         = $prompt
        tools                          = @($def.tools)
        triggers                       = $def.triggers
        enabled                        = -not $Disable
        require_actor_write_permission = $true
        run_limit                      = [int64]$def.run_limit_credits * $nano
        usage_limits                   = @(@{ period = 'day'; limit = [int64]$def.daily_limit_credits * $nano })
    }
    if ($existing.ContainsKey($def.name)) {
        $id = $existing[$def.name].id
        $r = Invoke-Gh PATCH "$api/$id" $body
        Write-Host "Updated  $($def.name) ($id)"
    } else {
        $body['type'] = $def.type
        $r = Invoke-Gh POST $api $body
        Write-Host "Created  $($def.name) ($($r.id))"
    }
    $installed[$def.name] = $r.id
}

$installed | ConvertTo-Json
