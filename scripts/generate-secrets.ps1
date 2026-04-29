<#
.SYNOPSIS
    Generates a .env file with strong random passwords for the SOC Lab.
.DESCRIPTION
    Native PowerShell (no bash dependency). Safe to run on any Windows machine.
    Will NOT overwrite an existing .env unless -Force is passed.
.EXAMPLE
    .\generate-secrets.ps1
    .\generate-secrets.ps1 -Force
#>

param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Write-Step { param($Msg) Write-Host "`n==> $Msg" -ForegroundColor Cyan }
function Write-OK   { param($Msg) Write-Host "  [OK]   $Msg" -ForegroundColor Green }
function Write-Info { param($Msg) Write-Host "  [INFO] $Msg" -ForegroundColor White }
function Write-Warn2{ param($Msg) Write-Host "  [WARN] $Msg" -ForegroundColor Yellow }

# Move to project root (one level up from scripts/)
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$envPath = Join-Path $ProjectRoot ".env"

function Test-LegacyEnv {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $false }
    $text = Get-Content $Path -Raw
    return ($text -match 'WAZUH_MANAGER_VERSION|THEHIVE_VERSION|CORTEX_VERSION|SHUFFLE_VERSION|OLLAMA_VERSION')
}

if ((Test-Path $envPath) -and (-not $Force)) {
    if (Test-LegacyEnv -Path $envPath) {
        Write-Warn2 "Detected legacy .env from old stack (Wazuh/TheHive/Shuffle/Ollama)."
        Write-Info  "Run this to migrate credentials for the new stack:"
        Write-Info  "  .\scripts\generate-secrets.ps1 -Force"
        Write-Info  "Then restart containers: .\scripts\launch-soc.ps1 -Rebuild"
        exit 0
    }
    Write-Warn2 ".env already exists. Use -Force to regenerate (this will invalidate current containers)."
    exit 0
}

if ((Test-Path $envPath) -and $Force) {
    $backupPath = Join-Path $ProjectRoot (".env.backup-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
    Copy-Item -Path $envPath -Destination $backupPath -Force
    Write-Info "Existing .env backed up to: $backupPath"
}

Write-Step "Generating strong secrets"

# ---- Secret generators ----
function New-Password {
    param([int]$Length = 24)
    # Alphanumeric only - avoids shell-escaping pain in docker-compose
    $chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    -join (1..$Length | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] })
}

function New-HexKey {
    param([int]$Bytes = 32)
    $b = New-Object byte[] $Bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
    ($b | ForEach-Object { $_.ToString("x2") }) -join ""
}

# ---- Versions pinned so the team gets identical environments ----
$envContent = @"
# =====================================================
#  SOC Lab - Environment Configuration
#  Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
#  DO NOT COMMIT THIS FILE. It is in .gitignore.
# =====================================================

# ---------- Pinned versions (do not change without team agreement) ----------
NGINX_VERSION=alpine
COWRIE_VERSION=latest
FALCO_VERSION=latest
ELASTICSEARCH_VERSION=8.11.0
KIBANA_VERSION=8.11.0
LOKI_VERSION=latest
GRAFANA_VERSION=latest
MINIO_VERSION=latest

# ---------- Grafana ----------
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=$(New-Password 20)

# ---------- MinIO ----------
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=$(New-Password 24)

# ---------- External API keys (FILL IN MANUALLY if you want enrichment) ----------
# Get free keys from:
#   https://www.virustotal.com/gui/my-apikey
#   https://www.abuseipdb.com/account/api
VIRUSTOTAL_API_KEY=CHANGE_ME
ABUSEIPDB_API_KEY=CHANGE_ME

# ---------- Network ----------
# Set by configure-lan.ps1 when sharing with teammates
SOC_BIND_ADDRESS=127.0.0.1
"@

$envContent | Out-File -FilePath $envPath -Encoding ASCII -NoNewline

# Lock the file down (Windows ACL) - only current user can read it
try {
    $acl = Get-Acl $envPath
    $acl.SetAccessRuleProtection($true, $false)  # disable inheritance
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        "$env:USERDOMAIN\$env:USERNAME",
        "FullControl",
        "Allow"
    )
    $acl.SetAccessRule($rule)
    Set-Acl -Path $envPath -AclObject $acl
    Write-OK "File permissions locked to current user only"
} catch {
    Write-Warn2 "Could not lock file ACL: $_"
}

Write-OK  "Generated $envPath"
Write-Info "Open .env in VS Code and (optionally) add your VirusTotal & AbuseIPDB keys:"
Write-Info "  code .env"
Write-Host ""
Write-Warn2 "NEVER commit .env to Git. It is ignored, but double-check with 'git status' before pushing."
Write-Host ""
