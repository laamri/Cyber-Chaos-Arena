<#
.SYNOPSIS
    Configures Windows Firewall and Docker bindings so teammates on the same LAN can reach your SOC Lab.
.DESCRIPTION
    - Detects your LAN IP
    - Opens Windows Firewall for the SOC Lab ports (TCP)
    - Updates .env to set SOC_BIND_ADDRESS=0.0.0.0 so Docker binds on all interfaces
    - Prints the share URLs for your teammate
.NOTES
    Must run as Administrator (for firewall changes).
    You'll need to restart the stack after this: .\launch-soc.ps1 -Rebuild
.EXAMPLE
    .\configure-lan.ps1
    .\configure-lan.ps1 -Revert     # close ports and bind back to localhost
#>

#Requires -RunAsAdministrator

param(
    [switch]$Revert
)

$ErrorActionPreference = "Stop"

function Write-Step { param($Msg) Write-Host "`n==> $Msg" -ForegroundColor Cyan }
function Write-OK   { param($Msg) Write-Host "  [OK]   $Msg" -ForegroundColor Green }
function Write-Info { param($Msg) Write-Host "  [INFO] $Msg" -ForegroundColor White }
function Write-Warn2{ param($Msg) Write-Host "  [WARN] $Msg" -ForegroundColor Yellow }

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EnvFile     = Join-Path $ProjectRoot ".env"
Set-Location $ProjectRoot

# Ports the SOC Lab exposes
$ports = @(
    @{ Port = 80;    Name = "SOC-Lab-Nginx-HTTP" },
    @{ Port = 443;   Name = "SOC-Lab-Nginx-HTTPS" },
    @{ Port = 8080;  Name = "SOC-Lab-Nginx-HTTP-Alt" },
    @{ Port = 8443;  Name = "SOC-Lab-Nginx-HTTPS-Alt" },
    @{ Port = 2222;  Name = "SOC-Lab-Cowrie" },
    @{ Port = 9200;  Name = "SOC-Lab-Elasticsearch" },
    @{ Port = 5601;  Name = "SOC-Lab-Kibana-SIEM" },
    @{ Port = 3100;  Name = "SOC-Lab-Loki" },
    @{ Port = 3000;  Name = "SOC-Lab-Grafana" },
    @{ Port = 9000;  Name = "SOC-Lab-MinIO-API" },
    @{ Port = 9001;  Name = "SOC-Lab-MinIO-Console" }
)

# ============================================================
#  Revert mode
# ============================================================
if ($Revert) {
    Write-Step "Reverting LAN exposure"
    foreach ($p in $ports) {
        $rule = Get-NetFirewallRule -DisplayName $p.Name -ErrorAction SilentlyContinue
        if ($rule) {
            Remove-NetFirewallRule -DisplayName $p.Name
            Write-OK "Removed firewall rule: $($p.Name)"
        }
    }
    if (Test-Path $EnvFile) {
        (Get-Content $EnvFile) -replace '^SOC_BIND_ADDRESS=.*','SOC_BIND_ADDRESS=127.0.0.1' |
            Set-Content $EnvFile -Encoding ASCII
        Write-OK "Bound services back to 127.0.0.1"
    }
    Write-Info "Restart the stack: .\launch-soc.ps1 -Rebuild"
    exit 0
}

# ============================================================
#  Detect LAN IP
# ============================================================
Write-Step "Detecting LAN IP"

# Prefer IPv4 address on the active (non-loopback, non-virtual) interface
$lanIp = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike '127.*' -and
        $_.IPAddress -notlike '169.254.*' -and
        $_.PrefixOrigin -ne 'WellKnown' -and
        $_.InterfaceAlias -notlike '*Loopback*' -and
        $_.InterfaceAlias -notlike '*WSL*' -and
        $_.InterfaceAlias -notlike '*vEthernet*' -and
        $_.InterfaceAlias -notlike '*Docker*'
    } | Select-Object -First 1).IPAddress

if (-not $lanIp) {
    Write-Warn2 "Could not auto-detect LAN IP. Listing all IPv4 addresses:"
    Get-NetIPAddress -AddressFamily IPv4 |
        Select-Object InterfaceAlias, IPAddress |
        Format-Table -AutoSize
    $lanIp = Read-Host "Enter the IP address to use (the one your friend can reach)"
}
Write-OK "LAN IP: $lanIp"

# ============================================================
#  Open Windows Firewall
# ============================================================
Write-Step "Opening Windows Firewall for SOC Lab ports"
Write-Warn2 "This exposes services on your LAN. Only do this on trusted networks."
$confirm = Read-Host "Continue? (y/N)"
if ($confirm -ne 'y') { Write-Info "Aborted."; exit 0 }

foreach ($p in $ports) {
    $proto = if ($p.Protocol) { $p.Protocol } else { "TCP" }
    $existing = Get-NetFirewallRule -DisplayName $p.Name -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Info "Rule '$($p.Name)' already exists - skipping"
        continue
    }
    New-NetFirewallRule `
        -DisplayName $p.Name `
        -Direction Inbound `
        -Protocol $proto `
        -LocalPort $p.Port `
        -Action Allow `
        -Profile Private `
        -Description "SOC Lab - auto-created by configure-lan.ps1" | Out-Null
    Write-OK "Opened $proto/$($p.Port) ($($p.Name))"
}

Write-Warn2 "Rules were created for the 'Private' network profile only."
Write-Info  "Make sure your current WiFi is set to 'Private' in Windows Settings > Network."

# ============================================================
#  Bind Docker to all interfaces
# ============================================================
Write-Step "Updating .env to bind services on all interfaces"
if (-not (Test-Path $EnvFile)) {
    Write-Warn2 ".env not found. Run generate-secrets.ps1 first."
    exit 1
}

$envText = Get-Content $EnvFile -Raw
if ($envText -match '^SOC_BIND_ADDRESS=') {
    $envText = $envText -replace 'SOC_BIND_ADDRESS=.*', 'SOC_BIND_ADDRESS=0.0.0.0'
} else {
    $envText += "`nSOC_BIND_ADDRESS=0.0.0.0"
}
$envText | Set-Content $EnvFile -Encoding ASCII -NoNewline
Write-OK "SOC_BIND_ADDRESS=0.0.0.0 written to .env"
Write-Info "Your docker-compose.yml must use this variable in port mappings, e.g.:"
Write-Info '    ports:'
Write-Info '      - "${SOC_BIND_ADDRESS:-127.0.0.1}:9000:9000"'

# ============================================================
#  Summary
# ============================================================
Write-Host ""
Write-Host "+---------------- SHARE WITH YOUR TEAMMATE ----------------+" -ForegroundColor Green
Write-Host "|                                                          |" -ForegroundColor Green
Write-Host ("|  LAN IP:  {0,-46} |" -f $lanIp) -ForegroundColor White
Write-Host "|                                                          |" -ForegroundColor Green
Write-Host ("|  Nginx HTTP      http://{0}:8080" -f $lanIp) -ForegroundColor White
Write-Host ("|  Nginx HTTPS     https://{0}:8443" -f $lanIp) -ForegroundColor White
Write-Host ("|  Cowrie SSH      ssh -p 2222 root@{0}" -f $lanIp) -ForegroundColor White
Write-Host ("|  Grafana         http://{0}:3000" -f $lanIp) -ForegroundColor White
Write-Host ("|  Elasticsearch   http://{0}:9200" -f $lanIp) -ForegroundColor White
Write-Host ("|  Kibana SIEM     http://{0}:5601" -f $lanIp) -ForegroundColor White
Write-Host ("|  Loki            http://{0}:3100" -f $lanIp) -ForegroundColor White
Write-Host ("|  MinIO API       http://{0}:9000" -f $lanIp) -ForegroundColor White
Write-Host ("|  MinIO Console   http://{0}:9001" -f $lanIp) -ForegroundColor White
Write-Host "|                                                          |" -ForegroundColor Green
Write-Host "+----------------------------------------------------------+" -ForegroundColor Green
Write-Host ""
Write-Info "Restart the stack to apply the bind change:"
Write-Info "  .\launch-soc.ps1 -Rebuild"
Write-Host ""
Write-Warn2 "Share CREDENTIALS with your teammate via a secure channel (Signal, 1Password, etc)"
Write-Warn2 "DO NOT send .env over Slack/Discord/Email."
Write-Host ""
