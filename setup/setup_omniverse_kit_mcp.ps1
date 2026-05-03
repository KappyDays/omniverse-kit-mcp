# setup_omniverse_kit_mcp.ps1 — Clone omniverse-kit-mcp repo, uv sync, register MCP server
# Run via: setup-omniverse-kit-mcp.bat (same directory)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

$RepoUrl    = "https://github.com/KappyDays/omniverse-kit-mcp.git"
$RepoDir    = Join-Path $env:USERPROFILE "workspace\omniverse-kit-mcp"
$ClaudeJson = Join-Path $env:USERPROFILE ".claude.json"
$McpName    = "omniverse-kit-mcp"

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "   Omniverse Kit MCP Server Setup                          " -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

# ── Step 1: Check prerequisites ─────────────────────────────────────────────

Write-Host ""
Write-Host "[ 1/5 ] Checking prerequisites..." -ForegroundColor Yellow

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
Write-Host "[ 2/5 ] Checking repo at $RepoDir ..." -ForegroundColor Yellow

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
Write-Host "[ 3/5 ] Checking .env configuration..." -ForegroundColor Yellow

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

# ── Step 4: Cleanup legacy global mcpServers entries ────────────────────────
# In-repo workspaces/<profile>/instance-<N>/.mcp.json (per-machine generated
# from .mcp.json.template) is now SoT. Remove 7 legacy entries that previous
# setup runs may have left in ~/.claude.json global mcpServers.

Write-Host ""
Write-Host "[ 4/5 ] Cleaning legacy MCP entries in $ClaudeJson ..." -ForegroundColor Yellow

if (Test-Path $ClaudeJson) {
    try {
        $claudeConfig = Get-Content $ClaudeJson -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        Write-Host "  [WARN] Failed to parse existing .claude.json. Skipping cleanup." -ForegroundColor Yellow
        $claudeConfig = $null
    }

    if ($null -ne $claudeConfig -and $claudeConfig.PSObject.Properties['mcpServers']) {
        $legacyNames = @(
            'isaacsim-mcp-1','isaacsim-mcp-2','isaacsim-mcp-3',
            'usdcomposer-mcp-1','usdcomposer-mcp-2','usdcomposer-mcp-3',
            'omniverse-kit-mcp'
        )
        $removed = 0
        foreach ($name in $legacyNames) {
            if ($claudeConfig.mcpServers.PSObject.Properties[$name]) {
                $claudeConfig.mcpServers.PSObject.Properties.Remove($name)
                $removed++
                Write-Host "  [OK]   Removed legacy '$name'" -ForegroundColor Green
            }
        }

        if ($removed -gt 0) {
            Save-JsonFile -Data $claudeConfig -Path $ClaudeJson
            Write-Host "  [OK]   Saved $ClaudeJson ($removed legacy entries removed)" -ForegroundColor Green
        } else {
            Write-Host "  [OK]   No legacy entries to clean." -ForegroundColor Green
        }
    }
} else {
    Write-Host "  [INFO] $ClaudeJson does not exist. Nothing to clean." -ForegroundColor DarkGray
}

# ── Step 5: Generate per-folder .mcp.json from templates ────────────────────
# 4 instance folders × {isaac, usd-composer} → .mcp.json with absolute $RepoDir
# substituted into {{REPO_DIR}} placeholder. Generated files are gitignored.

Write-Host ""
Write-Host "[ 5/5 ] Generating workspace .mcp.json from templates ..." -ForegroundColor Yellow

$WorkspacesDir = Join-Path $RepoDir "workspaces"
$RepoDirFwd    = ($RepoDir -replace '\\', '/')

$Instances = @(
    "isaac/instance-1",
    "isaac/instance-2",
    "usd-composer/instance-1",
    "usd-composer/instance-2"
)

$generated = 0
foreach ($rel in $Instances) {
    $instanceDir  = Join-Path $WorkspacesDir $rel
    $templatePath = Join-Path $instanceDir ".mcp.json.template"
    $mcpJsonPath  = Join-Path $instanceDir ".mcp.json"

    if (-not (Test-Path $templatePath)) {
        Write-Host "  [WARN] template missing: $templatePath" -ForegroundColor Yellow
        continue
    }

    $templateContent = Get-Content -Raw -Encoding UTF8 -Path $templatePath
    $rendered        = $templateContent -replace '\{\{REPO_DIR\}\}', $RepoDirFwd

    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($mcpJsonPath, $rendered, $utf8)
    $generated++
    Write-Host "  [OK]   Generated $rel/.mcp.json" -ForegroundColor Green
}

Write-Host ""
Write-Host "  $generated workspace .mcp.json files generated (REPO_DIR=$RepoDirFwd)" -ForegroundColor White

# ── Done ────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "======================================================" -ForegroundColor Green
Write-Host "   Omniverse Kit MCP setup complete!                       " -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor White
Write-Host "  1. Ensure Isaac Sim installed at:" -ForegroundColor Cyan
Write-Host "     C:\Users\$env:USERNAME\workspace\branch\isaac-sim-standalone-5.1.0-windows-x86_64\" -ForegroundColor DarkGray
Write-Host "  2. Ensure USD Composer built at:" -ForegroundColor Cyan
Write-Host "     C:\Users\$env:USERNAME\workspace\branch\kit-app-template\_build\windows-x86_64\release\" -ForegroundColor DarkGray
Write-Host "  3. cd into a workspace folder + start Claude Code:" -ForegroundColor Cyan
Write-Host "     cd workspaces\isaac\instance-1     # Isaac Sim instance 1, port 8011" -ForegroundColor DarkGray
Write-Host "     cd workspaces\usd-composer\instance-1  # USD Composer instance 1, port 8014" -ForegroundColor DarkGray
Write-Host "  4. Tools appear with prefix:" -ForegroundColor Cyan
Write-Host "     mcp__isaacsim-mcp-{1,2}__*       (Isaac instance)" -ForegroundColor DarkGray
Write-Host "     mcp__usdcomposer-mcp-{1,2}__*    (USD Composer instance)" -ForegroundColor DarkGray
Write-Host ""
