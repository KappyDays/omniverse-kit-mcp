# setup_isaacsim_mcp.ps1 — Clone Isaac-sim-MCP repo, uv sync, register MCP server
# Run via: setup-isaacsim-mcp.bat (same directory)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

$RepoUrl    = "https://github.com/KappyDays/Isaac-sim-MCP.git"
$RepoDir    = Join-Path $env:USERPROFILE "workspace\branch\Isaac-sim-MCP"
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

# ── Step 4: Register in ~/.claude.json ──────────────────────────────────────

Write-Host ""
Write-Host "[ 4/4 ] Registering MCP server in $ClaudeJson ..." -ForegroundColor Yellow

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

# uv --directory <repo> run isaacsim-mcp  (wrapped in cmd /c for Windows MCP)
$mcpEntry = [PSCustomObject]@{
    type    = "stdio"
    command = "cmd"
    args    = @("/c", "uv", "--directory", ($RepoDir -replace '\\', '/'), "run", "isaacsim-mcp")
    env     = [PSCustomObject]@{}
}

if ($claudeConfig.mcpServers.PSObject.Properties[$McpName]) {
    $claudeConfig.mcpServers.$McpName = $mcpEntry
    Write-Host "  [OK]   Updated existing '$McpName' entry." -ForegroundColor Green
} else {
    $claudeConfig.mcpServers | Add-Member -MemberType NoteProperty -Name $McpName -Value $mcpEntry
    Write-Host "  [OK]   Added new '$McpName' entry." -ForegroundColor Green
}

Save-JsonFile -Data $claudeConfig -Path $ClaudeJson
Write-Host "  [OK]   Saved to $ClaudeJson" -ForegroundColor Green

# ── Done ────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "======================================================" -ForegroundColor Green
Write-Host "   Isaac Sim MCP setup complete!                       " -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor White
Write-Host "  1. Open Isaac Sim" -ForegroundColor Cyan
Write-Host "  2. Window > Extensions > search 'Validation'" -ForegroundColor Cyan
Write-Host "     Add search path: $RepoDir\isaac_extension" -ForegroundColor DarkGray
Write-Host "  3. Enable 'Validation API Extension'" -ForegroundColor Cyan
Write-Host "  4. Verify: http://localhost:8011/validation/v1/health" -ForegroundColor Cyan
Write-Host "  5. Restart Claude Code to activate the MCP server" -ForegroundColor Cyan
Write-Host ""
