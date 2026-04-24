# setup_isaacsim_mcp.ps1 — Clone Isaac-sim-MCP repo, uv sync, register MCP server
# Run via: setup-isaacsim-mcp.bat (same directory)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

$RepoUrl    = "https://github.com/KappyDays/Isaac-sim-MCP.git"
$RepoDir    = Join-Path $env:USERPROFILE "workspace\Isaac-sim-MCP"
$ClaudeJson = Join-Path $env:USERPROFILE ".claude.json"
$McpName    = "isaacsim-mcp"

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "   Isaac Sim MCP Server Setup                          " -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

# ── Step 1: Check prerequisites ─────────────────────────────────────────────

Write-Host ""
Write-Host "[ 1/4 ] Checking prerequisites..." -ForegroundColor Yellow

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "  [FAIL] git not found. Please install Git and try again." -ForegroundColor Red
    exit 1
}
Write-Host "  [OK]   git: $(git --version)" -ForegroundColor Green

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "  [FAIL] uv not found. Install: 'pip install uv' or 'winget install astral-sh.uv'" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK]   uv: $(uv --version)" -ForegroundColor Green

# ── Step 2: Clone or verify repo ────────────────────────────────────────────

Write-Host ""
Write-Host "[ 2/4 ] Checking repo at $RepoDir ..." -ForegroundColor Yellow

$PyprojectFile = Join-Path $RepoDir "pyproject.toml"

if (Test-Path $PyprojectFile) {
    Write-Host "  [OK]   Already exists: $RepoDir" -ForegroundColor Green
    Write-Host "         Running uv sync to ensure deps are up to date..." -ForegroundColor DarkGray
    Push-Location $RepoDir
    uv sync --quiet
    Pop-Location
    Write-Host "  [OK]   uv sync done." -ForegroundColor Green
} else {
    # Create parent directory if needed
    $ParentDir = Split-Path -Parent $RepoDir
    if (-not (Test-Path $ParentDir)) {
        New-Item -ItemType Directory -Path $ParentDir -Force | Out-Null
    }

    if (Test-Path $RepoDir) {
        Write-Host "  [WARN] Directory exists but pyproject.toml missing. Re-cloning..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $RepoDir
    }

    Write-Host "  Cloning from $RepoUrl ..." -ForegroundColor DarkGray
    git clone $RepoUrl $RepoDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [FAIL] git clone failed." -ForegroundColor Red
        exit 1
    }
    Write-Host "  [OK]   Clone complete." -ForegroundColor Green

    Write-Host "  Running uv sync..." -ForegroundColor DarkGray
    Push-Location $RepoDir
    uv sync
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [FAIL] uv sync failed." -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Pop-Location
    Write-Host "  [OK]   uv sync done." -ForegroundColor Green
}

# ── Step 3: Create .env if missing ──────────────────────────────────────────

Write-Host ""
Write-Host "[ 3/4 ] Checking .env configuration..." -ForegroundColor Yellow

$EnvFile    = Join-Path $RepoDir ".env"
$EnvExample = Join-Path $RepoDir ".env.example"

if (Test-Path $EnvFile) {
    Write-Host "  [OK]   .env already exists." -ForegroundColor Green
} elseif (Test-Path $EnvExample) {
    Copy-Item $EnvExample $EnvFile
    Write-Host "  [OK]   Created .env from .env.example (default: localhost:8011)" -ForegroundColor Green
} else {
    # Create minimal .env
    @"
ISAAC_SIM_BASE_URL=http://localhost:8011
ISAAC_SIM_TIMEOUT=30.0
MCP_SERVER_NAME=isaacsim-validation-mcp
MCP_SERVER_PORT=8080
SCENARIOS_DIR=scenarios
"@ | Set-Content -Path $EnvFile -Encoding UTF8
    Write-Host "  [OK]   Created minimal .env." -ForegroundColor Green
}

# ── JSON save helper (2-space indent, UTF-8 no BOM) ─────────────────────────

function Save-JsonFile {
    param([object]$Data, [string]$Path)
    $tmp  = [System.IO.Path]::GetTempFileName()
    $utf8 = New-Object System.Text.UTF8Encoding $false
    try {
        $jsonText = $Data | ConvertTo-Json -Depth 10
        [System.IO.File]::WriteAllText($tmp, $jsonText, $utf8)

        $nodeExe = $env:PATH -split ';' |
            Where-Object { $_ -ne '' } |
            ForEach-Object { Join-Path $_ 'node.exe' } |
            Where-Object { Test-Path $_ } |
            Select-Object -First 1
        if ($nodeExe) {
            $nodeScript = "const fs=require('fs');const raw=fs.readFileSync(process.argv[1],'utf8').replace(/^\uFEFF/,'');fs.writeFileSync(process.argv[1],JSON.stringify(JSON.parse(raw),null,2),'utf8');"
            $prevEAP = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            & $nodeExe -e $nodeScript $tmp 2>&1 | Out-Null
            $nodeExit = $LASTEXITCODE
            $ErrorActionPreference = $prevEAP
            if ($nodeExit -ne 0) {
                [System.IO.File]::WriteAllText($tmp, $jsonText, $utf8)
            }
        }
        [System.IO.File]::WriteAllText(
            $Path,
            [System.IO.File]::ReadAllText($tmp, [System.Text.Encoding]::UTF8),
            $utf8
        )
    } finally {
        Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    }
}

# ── Step 4: Register in ~/.claude.json (multi-instance × multi-app) ──────

Write-Host ""
Write-Host "[ 4/4 ] Registering MCP servers in $ClaudeJson ..." -ForegroundColor Yellow

if (Test-Path $ClaudeJson) {
    try {
        $claudeConfig = Get-Content $ClaudeJson -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        Write-Host "  [WARN] Failed to parse existing .claude.json. Aborting." -ForegroundColor Red
        exit 1
    }
} else {
    $claudeConfig = [PSCustomObject]@{}
}

if (-not $claudeConfig.PSObject.Properties['mcpServers']) {
    $claudeConfig | Add-Member -MemberType NoteProperty -Name 'mcpServers' -Value ([PSCustomObject]@{})
}

# Multi-instance × multi-app matrix. Profile base ports:
#   isaac-sim     -> 8011, 8012, 8013
#   usd-composer  -> 8014, 8015, 8016
$InstanceCount = 3
$Profiles = @(
    @{ name = "isaac-sim";    prefix = "isaacsim-mcp" },
    @{ name = "usd-composer"; prefix = "usdcomposer-mcp" }
)

function Make-McpEntry($ProfileName, $InstanceId) {
    # --no-sync is CRITICAL for multi-instance: every `uv run` without it
    # triggers `uv sync`, which tries to reinstall the editable isaacsim-mcp
    # package. When multiple MCP servers run simultaneously (6 entries), each
    # sync competes to replace the same `.venv/Scripts/isaacsim-mcp.exe` —
    # the first one wins (locks it), every subsequent sync fails with
    # "The process cannot access the file because it is being used by another
    # process", and `uv run isaacsim-mcp` never spawns the server. Claude
    # Code then reports "Failed to reconnect" for those entries.
    # Setup script step 2 already runs `uv sync` once, so --no-sync here is
    # safe.
    return [PSCustomObject]@{
        type    = "stdio"
        command = "cmd"
        args    = @("/c", "uv", "--directory", ($RepoDir -replace '\\', '/'), "run", "--no-sync", "isaacsim-mcp")
        env     = [PSCustomObject]@{
            ISAAC_MCP_APP_PROFILE = $ProfileName
            ISAAC_MCP_INSTANCE_ID = "$InstanceId"
        }
    }
}

function Set-McpEntry($EntryName, $Entry) {
    if ($claudeConfig.mcpServers.PSObject.Properties[$EntryName]) {
        $claudeConfig.mcpServers.$EntryName = $Entry
        Write-Host "  [OK]   Updated '$EntryName'" -ForegroundColor Green
    } else {
        $claudeConfig.mcpServers | Add-Member -MemberType NoteProperty -Name $EntryName -Value $Entry
        Write-Host "  [OK]   Added   '$EntryName'" -ForegroundColor Green
    }
}

foreach ($prof in $Profiles) {
    for ($i = 1; $i -le $InstanceCount; $i++) {
        $entryName = "$($prof.prefix)-$i"
        Set-McpEntry $entryName (Make-McpEntry $prof.name $i)
    }
}

# Legacy alias 'isaacsim-mcp' → isaac-sim instance 1 (backward compat)
Set-McpEntry "isaacsim-mcp" (Make-McpEntry "isaac-sim" 1)

Save-JsonFile -Data $claudeConfig -Path $ClaudeJson
Write-Host "  [OK]   Saved to $ClaudeJson" -ForegroundColor Green

Write-Host ""
Write-Host "  Registered MCP servers:" -ForegroundColor White
Write-Host "    isaacsim-mcp          (alias -> isaac-sim instance 1, port 8011)" -ForegroundColor DarkGray
foreach ($i in 1..$InstanceCount) {
    Write-Host "    isaacsim-mcp-$i       (isaac-sim instance $i, port $(8010 + $i))" -ForegroundColor DarkGray
}
foreach ($i in 1..$InstanceCount) {
    Write-Host "    usdcomposer-mcp-$i    (usd-composer instance $i, port $(8013 + $i))" -ForegroundColor DarkGray
}

# ── Done ────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "======================================================" -ForegroundColor Green
Write-Host "   Isaac Sim MCP setup complete!                       " -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor White
Write-Host "  1. Ensure Isaac Sim installed at:" -ForegroundColor Cyan
Write-Host "     C:\Users\$env:USERNAME\workspace\branch\isaac-sim-standalone-5.1.0-windows-x86_64\" -ForegroundColor DarkGray
Write-Host "  2. Ensure USD Composer built at:" -ForegroundColor Cyan
Write-Host "     C:\Users\$env:USERNAME\workspace\branch\kit-app-template\_build\windows-x86_64\release\" -ForegroundColor DarkGray
Write-Host "  3. Restart Claude Code to pick up new MCP entries" -ForegroundColor Cyan
Write-Host "  4. In Claude Code, use tools prefixed:" -ForegroundColor Cyan
Write-Host "     mcp__isaacsim-mcp-N__*      for Isaac Sim instance N" -ForegroundColor DarkGray
Write-Host "     mcp__usdcomposer-mcp-N__*   for USD Composer instance N" -ForegroundColor DarkGray
Write-Host ""
