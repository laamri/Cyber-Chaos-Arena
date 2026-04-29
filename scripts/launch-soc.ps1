<#
.SYNOPSIS
    Launches the SOC Lab stack and runs health checks.
.DESCRIPTION
    - Verifies Docker Desktop is running
    - Pulls pinned images
    - Starts the stack with docker compose
    - Waits for services to become healthy
    - Prints access URLs
.EXAMPLE
    .\launch-soc.ps1
    .\launch-soc.ps1 -Rebuild     # docker compose up --force-recreate
    .\launch-soc.ps1 -Stop        # stop the stack (keeps data)
    .\launch-soc.ps1 -Destroy     # nuke everything including volumes
#>

param(
    [switch]$Rebuild,
    [switch]$Stop,
    [switch]$Destroy
)

$ErrorActionPreference = "Stop"

function Write-Step { param($Msg) Write-Host "`n==> $Msg" -ForegroundColor Cyan }
function Write-OK   { param($Msg) Write-Host "  [OK]   $Msg" -ForegroundColor Green }
function Write-Info { param($Msg) Write-Host "  [INFO] $Msg" -ForegroundColor White }
function Write-Warn2{ param($Msg) Write-Host "  [WARN] $Msg" -ForegroundColor Yellow }
function Write-Err  { param($Msg) Write-Host "  [ERR]  $Msg" -ForegroundColor Red }

$ProjectRoot  = Split-Path -Parent $PSScriptRoot
$ComposeFile  = Join-Path $ProjectRoot "docker\docker-compose.yml"
$EnvFile      = Join-Path $ProjectRoot ".env"

Set-Location $ProjectRoot

# ============================================================
#  Preflight
# ============================================================
Write-Step "Preflight checks"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Err "Docker not found. Run bootstrap.ps1 first."
    exit 1
}

try {
    docker info --format "{{.ServerVersion}}" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "daemon down" }
} catch {
    Write-Err "Docker daemon is not running. Start Docker Desktop and wait for the whale icon to stabilize."
    exit 1
}
Write-OK "Docker daemon is running"

if (-not (Test-Path $EnvFile)) {
    Write-Err ".env not found. Run generate-secrets.ps1 first."
    exit 1
}
Write-OK ".env found"

$envText = Get-Content $EnvFile -Raw
$requiredVars = @("GRAFANA_ADMIN_USER", "GRAFANA_ADMIN_PASSWORD", "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD", "SOC_BIND_ADDRESS")
$missingVars = @()
foreach ($varName in $requiredVars) {
    if ($envText -notmatch "(?m)^$varName=") {
        $missingVars += $varName
    }
}

if ($missingVars.Count -gt 0) {
    Write-Err "Your .env does not match the new SOC stack. Missing: $($missingVars -join ', ')"
    Write-Info "Fix with: .\scripts\generate-secrets.ps1 -Force"
    Write-Info "Then run: .\scripts\launch-soc.ps1 -Rebuild"
    exit 1
}

if ($envText -match 'WAZUH_MANAGER_VERSION|THEHIVE_VERSION|CORTEX_VERSION|SHUFFLE_VERSION|OLLAMA_VERSION') {
    Write-Warn2 "Legacy keys detected in .env from the previous stack."
    Write-Info "Recommended: regenerate with .\scripts\generate-secrets.ps1 -Force"
}

$grafanaAdminUserLine = (($envText -split "`r?`n") | Where-Object { $_ -match '^GRAFANA_ADMIN_USER=' } | Select-Object -First 1)
$grafanaAdminPassLine = (($envText -split "`r?`n") | Where-Object { $_ -match '^GRAFANA_ADMIN_PASSWORD=' } | Select-Object -First 1)
$GrafanaAdminUser = if ($grafanaAdminUserLine) { ($grafanaAdminUserLine -replace '^GRAFANA_ADMIN_USER=', '').Trim() } else { "admin" }
$GrafanaAdminPassword = if ($grafanaAdminPassLine) { ($grafanaAdminPassLine -replace '^GRAFANA_ADMIN_PASSWORD=', '').Trim() } else { $null }

if (-not (Test-Path $ComposeFile)) {
    Write-Err "docker-compose.yml not found at $ComposeFile"
    Write-Info "You need to place your existing docker-compose.yml at: docker\docker-compose.yml"
    exit 1
}
Write-OK "docker-compose.yml found"

# ============================================================
#  Stop / Destroy shortcuts
# ============================================================
if ($Stop) {
    Write-Step "Stopping SOC Lab stack"
    docker compose --env-file $EnvFile -f $ComposeFile stop
    Write-OK "Stack stopped (data preserved). Start again with: .\launch-soc.ps1"
    exit 0
}

if ($Destroy) {
    Write-Step "DESTROYING SOC Lab stack (including volumes)"
    $confirm = Read-Host "This deletes ALL data. Type 'DESTROY' to confirm"
    if ($confirm -ne "DESTROY") {
        Write-Info "Aborted."
        exit 0
    }
    docker compose --env-file $EnvFile -f $ComposeFile down -v --remove-orphans
    Write-OK "Stack destroyed"
    exit 0
}

# ============================================================
#  Required images check
# ============================================================
Write-Step "Verifying required container images"

$requiredImages = @(
    "nginx:alpine",
    "cowrie/cowrie:latest",
    "falcosecurity/falco:latest",
    "elasticsearch:8.11.0",
    "kibana:8.11.0",
    "grafana/loki:latest",
    "grafana/grafana:latest",
    "minio/minio:latest",
    "docker.elastic.co/beats/filebeat:8.11.0"
)

foreach ($image in $requiredImages) {
    $imagePresent = $false
    try {
        docker image inspect $image 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $imagePresent = $true
        }
    } catch {
        $imagePresent = $false
    }

    if ($imagePresent) {
        Write-OK "$image already present"
        continue
    }

    Write-Info "Pulling missing image: $image"
    docker pull $image
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to pull required image: $image"
        exit 1
    }
    Write-OK "$image pulled"
}

# ============================================================
#  WSL2 kernel tuning (vm.max_map_count for Elasticsearch/OpenSearch)
# ============================================================
Write-Step "Tuning WSL2 kernel for Elasticsearch"
try {
    # Run inside the docker-desktop WSL distro
    wsl -d docker-desktop -- sh -c "sysctl -w vm.max_map_count=262144" 2>&1 | Out-Null
    Write-OK "vm.max_map_count=262144 set"
} catch {
    Write-Warn2 "Could not set vm.max_map_count. Elasticsearch may fail to start."
    Write-Info  "Manual fix: wsl -d docker-desktop -u root -- sysctl -w vm.max_map_count=262144"
}

# ============================================================
#  Pull images
# ============================================================
Write-Step "Pulling container images (this can take a few minutes the first time)"
docker compose --env-file $EnvFile -f $ComposeFile pull
if ($LASTEXITCODE -ne 0) {
    Write-Warn2 "Some images failed to pull. Continuing anyway - compose will retry."
}

# ============================================================
#  Start stack
# ============================================================
Write-Step "Starting SOC Lab stack"
$composeArgs = @("--env-file", $EnvFile, "-f", $ComposeFile, "up", "-d")
if ($Rebuild) { $composeArgs += "--force-recreate" }

docker compose @composeArgs
if ($LASTEXITCODE -ne 0) {
    Write-Err "docker compose up failed. Check logs with: docker compose logs"
    exit 1
}
Write-OK "Stack launched"

# ============================================================
#  Grafana credential sync (important when volume already exists)
# ============================================================
if ($GrafanaAdminPassword) {
    Write-Step "Syncing Grafana admin password from .env"
    $synced = $false
    for ($i = 1; $i -le 12; $i++) {
        docker exec grafana sh -c "grafana cli --homepath /usr/share/grafana admin reset-admin-password $GrafanaAdminPassword" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $synced = $true
            Write-OK "Grafana admin password synchronized for user '$GrafanaAdminUser'"
            break
        }
        Start-Sleep -Seconds 5
    }
    if (-not $synced) {
        Write-Warn2 "Could not sync Grafana password automatically."
        Write-Info 'Manual reset: docker exec grafana sh -c "grafana cli --homepath /usr/share/grafana admin reset-admin-password NEW_PASSWORD"'
    }
}

# ============================================================
#  Health check
# ============================================================
Write-Step "Waiting for services to become healthy (up to 5 minutes)"

$endpoints = @(
    @{ Name = "Nginx Router";     Url = "http://localhost:8080/health"; Method = "GET" },
    @{ Name = "Elasticsearch";    Url = "http://localhost:9200";        Method = "GET" },
    @{ Name = "Kibana SIEM";      Url = "http://localhost:5601";        Method = "HEAD" },
    @{ Name = "Filebeat";         Url = "http://localhost:5066";        Method = "GET" },
    @{ Name = "Loki";             Url = "http://localhost:3100/ready";  Method = "GET" },
    @{ Name = "Grafana";          Url = "http://localhost:3000/login";  Method = "HEAD" },
    @{ Name = "MinIO API";        Url = "http://localhost:9000/minio/health/live"; Method = "GET" },
    @{ Name = "MinIO Console";    Url = "http://localhost:9001/login";  Method = "HEAD" }
)

# Allow self-signed certs in PowerShell
Add-Type @"
using System.Net;
using System.Security.Cryptography.X509Certificates;
public class TrustAllCertsPolicy : ICertificatePolicy {
    public bool CheckValidationResult(ServicePoint srvPoint, X509Certificate certificate,
        WebRequest request, int certificateProblem) { return true; }
}
"@ -ErrorAction SilentlyContinue

[System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy
[System.Net.ServicePointManager]::SecurityProtocol = `
    [System.Net.SecurityProtocolType]::Tls12 -bor [System.Net.SecurityProtocolType]::Tls11

$timeout    = New-TimeSpan -Minutes 5
$sw         = [System.Diagnostics.Stopwatch]::StartNew()
$results    = @{}
$allReady   = $false

while ($sw.Elapsed -lt $timeout -and -not $allReady) {
    $allReady = $true
    foreach ($ep in $endpoints) {
        if ($results[$ep.Name] -eq $true) { continue }
        try {
            $r = Invoke-WebRequest -Uri $ep.Url -Method $ep.Method `
                -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
            if ($r.StatusCode -lt 500) {
                $results[$ep.Name] = $true
                Write-OK "$($ep.Name) responded ($($r.StatusCode))"
            } else { $allReady = $false }
        } catch {
            $allReady = $false
        }
    }

    if ($results["Cowrie Honeypot"] -ne $true) {
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $async = $tcp.BeginConnect("127.0.0.1", 2222, $null, $null)
            if ($async.AsyncWaitHandle.WaitOne(1500, $false) -and $tcp.Connected) {
                $tcp.EndConnect($async) | Out-Null
                $tcp.Close()
                $results["Cowrie Honeypot"] = $true
                Write-OK "Cowrie Honeypot port is open (2222)"
            } else {
                $tcp.Close()
                $allReady = $false
            }
        } catch {
            $allReady = $false
        }
    }

    if (-not $allReady) { Start-Sleep -Seconds 10 }
}

# ============================================================
#  Summary
# ============================================================
Write-Step "Container status"
docker compose --env-file $EnvFile -f $ComposeFile ps

Write-Host ""
Write-Host "+---------------------- ACCESS URLs ------------------------+" -ForegroundColor Cyan
Write-Host "|  Nginx Router      http://localhost:8080                 |" -ForegroundColor White
Write-Host "|  Real User Path    http://localhost:8080/                |" -ForegroundColor White
Write-Host "|  Attack Test Path  http://localhost:8080/wp-admin        |" -ForegroundColor White
Write-Host "|  Grafana           http://localhost:3000                 |" -ForegroundColor White
Write-Host "|  Elasticsearch     http://localhost:9200                 |" -ForegroundColor White
Write-Host "|  Kibana SIEM       http://localhost:5601                 |" -ForegroundColor White
Write-Host "|  Filebeat API      http://localhost:5066                 |" -ForegroundColor White
Write-Host "|  Loki              http://localhost:3100                 |" -ForegroundColor White
Write-Host "|  MinIO API         http://localhost:9000                 |" -ForegroundColor White
Write-Host "|  MinIO Console     http://localhost:9001                 |" -ForegroundColor White
Write-Host "|  Cowrie SSH        ssh -p 2222 root@localhost            |" -ForegroundColor White
Write-Host "+-----------------------------------------------------------+" -ForegroundColor Cyan
Write-Info "Credentials are in your .env file"

if (-not $allReady) {
    Write-Warn2 "Some services didn't respond within 5 minutes. They may still be starting."
    Write-Info  "Check container logs:  docker compose logs -f <service-name>"
    Write-Info  "Common slow services: elasticsearch, grafana, minio"
}
