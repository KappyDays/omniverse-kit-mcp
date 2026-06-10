$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$kitExe = Join-Path $scriptDir "kit/kit.exe"
$kitFile = Join-Path $scriptDir "apps/isaacsim.exp.full.kit"
$portByInstance = @{
    1 = 8111
    2 = 8112
}

$dryRun = $false
$requestedInstance = $null
$requestedPort = $null
$forwardArgs = New-Object System.Collections.Generic.List[string]

for ($i = 0; $i -lt $args.Count; $i++) {
    $arg = [string]$args[$i]
    switch ($arg) {
        "--dry-run" {
            $dryRun = $true
            continue
        }
        "--no-ros-env" {
            continue
        }
        "--instance" {
            if ($i + 1 -ge $args.Count) {
                throw "--instance requires 1 or 2"
            }
            $i++
            $requestedInstance = [int]$args[$i]
            continue
        }
        "--port" {
            if ($i + 1 -ge $args.Count) {
                throw "--port requires 8111 or 8112"
            }
            $i++
            $requestedPort = [int]$args[$i]
            continue
        }
        "--help" {
            Write-Host "Usage: isaac-sim_mcp.bat [--instance 1|2] [--port 8111|8112] [--dry-run] [Isaac Sim args...]"
            exit 0
        }
        default {
            $forwardArgs.Add($arg) | Out-Null
        }
    }
}

if ($requestedInstance -ne $null -and -not $portByInstance.ContainsKey($requestedInstance)) {
    throw "--instance must be 1 or 2"
}

if ($requestedPort -ne $null -and -not ($portByInstance.Values -contains $requestedPort)) {
    throw "--port must be 8111 or 8112"
}

if ($requestedInstance -ne $null -and $requestedPort -ne $null) {
    $expectedPort = $portByInstance[$requestedInstance]
    if ($requestedPort -ne $expectedPort) {
        throw "--instance $requestedInstance maps to port $expectedPort, not $requestedPort"
    }
}

function Test-PortAvailable {
    param([int]$Port)

    $listener = $null
    try {
        $endpoint = [System.Net.IPEndPoint]::new([System.Net.IPAddress]::Any, $Port)
        $listener = [System.Net.Sockets.TcpListener]::new($endpoint)
        $listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        if ($listener -ne $null) {
            $listener.Stop()
        }
    }
}

function New-PortMutex {
    param([int]$Port)

    $created = $false
    $mutex = [System.Threading.Mutex]::new($true, "Global\IsaacSimMcpPort$Port", [ref]$created)
    if (-not $created) {
        $mutex.Dispose()
        return $null
    }
    return $mutex
}

function Select-Port {
    $candidates = if ($requestedPort -ne $null) {
        @($requestedPort)
    } elseif ($requestedInstance -ne $null) {
        @($portByInstance[$requestedInstance])
    } else {
        @($portByInstance[1], $portByInstance[2])
    }

    foreach ($port in $candidates) {
        if (-not (Test-PortAvailable -Port $port)) {
            continue
        }
        $mutex = New-PortMutex -Port $port
        if ($mutex -eq $null) {
            continue
        }
        $instance = ($portByInstance.GetEnumerator() | Where-Object { $_.Value -eq $port } | Select-Object -First 1).Key
        return [pscustomobject]@{ Instance = [int]$instance; Port = [int]$port; Mutex = $mutex }
    }

    throw "No Isaac Sim MCP port available. Tried: $($candidates -join ', ')"
}

if (-not (Test-Path -LiteralPath $kitExe)) {
    throw "kit.exe not found: $kitExe"
}

if (-not (Test-Path -LiteralPath $kitFile)) {
    throw "Kit file not found: $kitFile"
}

$selection = Select-Port
$kitArgs = New-Object System.Collections.Generic.List[string]
$kitArgs.Add($kitFile) | Out-Null
$kitArgs.Add("--/exts/omni.services.transport.server.http/port=$($selection.Port)") | Out-Null
$kitArgs.Add("--/exts/omni.services.transport.server.http/allow_port_range=false") | Out-Null
foreach ($arg in $forwardArgs) {
    $kitArgs.Add($arg) | Out-Null
}

try {
    if ($dryRun) {
        [pscustomobject]@{
            instance = $selection.Instance
            port = $selection.Port
            kit_exe = $kitExe
            kit_file = $kitFile
            args = $kitArgs.ToArray()
        } | ConvertTo-Json -Depth 4
        exit 0
    }

    Write-Host "Starting Isaac Sim MCP instance $($selection.Instance) on port $($selection.Port)"
    & $kitExe @kitArgs
    exit $LASTEXITCODE
} finally {
    if ($selection.Mutex -ne $null) {
        $selection.Mutex.ReleaseMutex()
        $selection.Mutex.Dispose()
    }
}
