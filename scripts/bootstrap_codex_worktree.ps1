param(
    [ValidateSet("isaac-sim", "usd-composer")]
    [string]$Profile = "isaac-sim",

    [ValidateRange(1, 2)]
    [int]$Instance = 1,

    [string]$LocalEnvPath = "$env:USERPROFILE\.config\omniverse-kit-mcp\local.env",

    [switch]$SkipUvSync,

    [switch]$SkipMcpListCheck,

    [switch]$RefreshEnv
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
$mcpCwd = (Get-Location).Path
$repoEnv = Join-Path $repoRoot ".env"

Write-Host "== Codex worktree bootstrap ==" -ForegroundColor Cyan
Write-Host "repo:      $repoRoot"
Write-Host "profile:   $Profile"
Write-Host "instance:  $Instance"

if ((-not (Test-Path $repoEnv)) -or $RefreshEnv) {
    if (Test-Path $LocalEnvPath) {
        Copy-Item -LiteralPath $LocalEnvPath -Destination $repoEnv
        Write-Host "copied local env: $LocalEnvPath -> $repoEnv" -ForegroundColor Green
    } else {
        $dir = Split-Path -Parent $LocalEnvPath
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        Write-Host "missing local env: $LocalEnvPath" -ForegroundColor Yellow
        Write-Host "Create it with at least:" -ForegroundColor Yellow
        Write-Host "ISAAC_SIM_KIT_EXE=C:/path/to/isaac-sim/kit/kit.exe"
        Write-Host "ISAAC_SIM_KIT_FILE=C:/path/to/isaac-sim/apps/isaacsim.exp.full.kit"
    }
} else {
    Write-Host "repo .env already exists; leaving it unchanged"
    Write-Host "Use -RefreshEnv to replace it from $LocalEnvPath"
}

if (-not $SkipUvSync) {
    Push-Location $repoRoot
    try {
        Write-Host "running uv sync..."
        uv sync
    } finally {
        Pop-Location
    }
}

$env:ISAAC_MCP_APP_PROFILE = $Profile
$env:ISAAC_MCP_INSTANCE_ID = [string]$Instance

$verifyArgs = @(
    "--directory", $repoRoot, "run", "python", "scripts/verify_local_isaac_env.py",
    "--profile", $Profile,
    "--instance", [string]$Instance,
    "--repo-root", $repoRoot,
    "--mcp-cwd", $mcpCwd
)

if (-not $SkipMcpListCheck) {
    $verifyArgs += "--check-codex-mcp-list"
}

Write-Host "running local Isaac/Codex preflight..."
& uv @verifyArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
