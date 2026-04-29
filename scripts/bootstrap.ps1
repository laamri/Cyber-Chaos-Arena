<#
.SYNOPSIS
    SOC Lab Bootstrap Script for Windows
.DESCRIPTION
    Verifies and installs all prerequisites for the SOC Lab:
    - WSL2 (required by Docker Desktop)
    - Docker Desktop
    - Git
    - VS Code
    - OpenSSL (for cert generation)
    Idempotent: safe to run multiple times. Skips anything already installed.
.NOTES
    Run from an ELEVATED PowerShell (Administrator).
    Usage: powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1
#>

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# ============================================================
#  UI Helpers
# ============================================================
function Write-Step    { param($Msg) Write-Host "`n==> $Msg" -ForegroundColor Cyan }
function Write-OK      { param($Msg) Write-Host "  [OK]   $Msg" -ForegroundColor Green }
function Write-Skip    { param($Msg) Write-Host "  [SKIP] $Msg" -ForegroundColor DarkGray }
function Write-Warn2   { param($Msg) Write-Host "  [WARN] $Msg" -ForegroundColor Yellow }
function Write-Err     { param($Msg) Write-Host "  [ERR]  $Msg" -ForegroundColor Red }
function Write-Info    { param($Msg) Write-Host "  [INFO] $Msg" -ForegroundColor White }

function Test-CommandExists {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

function Test-WingetPackageInstalled {
    param([string]$Id)
    $result = winget list --id $Id --exact --accept-source-agreements 2>$null | Out-String
    return $result -match $Id
}

# ============================================================
#  Banner
# ============================================================
Clear-Host
Write-Host @"

  +----------------------------------------------+
  |         SOC Lab - Bootstrap Installer        |
  |         Windows Host Edition                  |
  +----------------------------------------------+

"@ -ForegroundColor Cyan

# ============================================================
#  Step 0: Environment sanity checks
# ============================================================
Write-Step "Checking environment"

# Check Windows version (Docker Desktop needs Win10 2004+ or Win11)
$win = [System.Environment]::OSVersion.Version
Write-Info "Windows version: $($win.Major).$($win.Minor) Build $($win.Build)"
if ($win.Build -lt 19041) {
    Write-Err "Windows 10 build 19041+ or Windows 11 required for WSL2."
    exit 1
}
Write-OK "Windows version is compatible"

# Check winget is available
if (-not (Test-CommandExists "winget")) {
    Write-Err "winget not found. Install 'App Installer' from the Microsoft Store, then rerun this script."
    Start-Process "ms-windows-store://pdp/?ProductId=9NBLGGH4NNS1"
    exit 1
}
Write-OK "winget is available"

# Check virtualization is enabled
$hvInfo = Get-ComputerInfo -Property "HyperV*" -ErrorAction SilentlyContinue
$virt = (Get-CimInstance -ClassName Win32_Processor).VirtualizationFirmwareEnabled
if ($virt -eq $false) {
    Write-Warn2 "Hardware virtualization appears DISABLED in BIOS."
    Write-Warn2 "Docker Desktop will NOT work until you enable Intel VT-x / AMD-V in BIOS."
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne 'y') { exit 1 }
} else {
    Write-OK "Hardware virtualization is enabled"
}

# ============================================================
#  Step 1: WSL2
# ============================================================
Write-Step "Checking WSL2"

$wslInstalled = $false
try {
    $wslStatus = wsl --status 2>&1
    if ($LASTEXITCODE -eq 0) {
        $wslInstalled = $true
        Write-Skip "WSL is already installed"
    }
} catch {}

if (-not $wslInstalled) {
    Write-Info "Installing WSL2 (this enables the required Windows features)..."
    try {
        wsl --install --no-distribution
        Write-OK "WSL2 installed. A reboot will be required before running this script again."
        Write-Warn2 "Please REBOOT your computer now, then rerun this script."
        Read-Host "Press ENTER to exit"
        exit 0
    } catch {
        Write-Err "WSL install failed: $_"
        exit 1
    }
}

# Ensure WSL default version is 2
try {
    wsl --set-default-version 2 2>&1 | Out-Null
    Write-OK "WSL default version set to 2"
} catch {
    Write-Warn2 "Could not set WSL default version to 2 (may already be set)"
}

# ============================================================
#  Step 2: Core tools via winget
# ============================================================
Write-Step "Installing core tools"

$packages = @(
    @{ Id = "Git.Git";                    Name = "Git" },
    @{ Id = "Microsoft.VisualStudioCode"; Name = "VS Code" },
    @{ Id = "Docker.DockerDesktop";       Name = "Docker Desktop" },
    @{ Id = "ShiningLight.OpenSSL.Light"; Name = "OpenSSL (Light)" }
)

foreach ($pkg in $packages) {
    if (Test-WingetPackageInstalled -Id $pkg.Id) {
        Write-Skip "$($pkg.Name) already installed"
        continue
    }
    Write-Info "Installing $($pkg.Name)..."
    try {
        winget install --id $pkg.Id --exact --silent `
            --accept-source-agreements --accept-package-agreements | Out-Null
        Write-OK "$($pkg.Name) installed"
    } catch {
        Write-Warn2 "Failed to install $($pkg.Name) via winget: $_"
    }
}

# ============================================================
#  Step 3: Refresh PATH so new commands are usable in this session
# ============================================================
Write-Step "Refreshing environment variables"

$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")
Write-OK "PATH refreshed"

# ============================================================
#  Step 4: Verify Docker Desktop
# ============================================================
Write-Step "Verifying Docker Desktop"

if (-not (Test-CommandExists "docker")) {
    Write-Warn2 "'docker' command not found in PATH yet."
    Write-Warn2 "Docker Desktop was just installed and may require a REBOOT before first use."
    Write-Info  "After reboot:"
    Write-Info  "  1. Launch Docker Desktop from the Start menu"
    Write-Info  "  2. Accept the license terms"
    Write-Info  "  3. Wait for the whale icon in the system tray to be steady (not animating)"
    Write-Info  "  4. Rerun this script to verify, then run launch-soc.ps1"
    exit 0
}

# Try to contact the Docker daemon
try {
    docker info --format "{{.ServerVersion}}" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $dockerVer = docker --version
        Write-OK "Docker is running ($dockerVer)"
    } else {
        Write-Warn2 "Docker Desktop is installed but the daemon isn't running."
        Write-Info  "Start Docker Desktop from the Start menu and wait for the whale icon to stabilize."
        exit 0
    }
} catch {
    Write-Warn2 "Could not contact Docker daemon. Start Docker Desktop manually."
    exit 0
}

# Check docker compose plugin
try {
    docker compose version 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-OK "Docker Compose plugin is working"
    }
} catch {
    Write-Warn2 "Docker Compose plugin not detected"
}

# ============================================================
#  Step 5: WSL2 resource tuning (.wslconfig)
# ============================================================
Write-Step "Tuning WSL2 resource limits for 16 GB host"

$wslConfigPath = "$env:USERPROFILE\.wslconfig"
$wslConfigContent = @"
# Generated by SOC Lab bootstrap
# Tuned for a 16 GB host running the SOC stack in Docker Desktop (WSL2 backend)
[wsl2]
memory=10GB
processors=4
swap=4GB
localhostForwarding=true
"@

if (Test-Path $wslConfigPath) {
    Write-Skip ".wslconfig already exists at $wslConfigPath (not overwriting)"
    Write-Info  "If the stack is slow, review it and consider: memory=10GB, processors=4"
} else {
    $wslConfigContent | Out-File -FilePath $wslConfigPath -Encoding ASCII
    Write-OK "Wrote $wslConfigPath"
    Write-Info "Apply it with: wsl --shutdown    (then restart Docker Desktop)"
}

# ============================================================
#  Done
# ============================================================
Write-Host ""
Write-Host "+----------------------------------------------+" -ForegroundColor Green
Write-Host "|  Bootstrap complete                          |" -ForegroundColor Green
Write-Host "+----------------------------------------------+" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Make sure Docker Desktop is running (whale icon steady)" -ForegroundColor White
Write-Host "  2. Run: .\generate-secrets.ps1     (creates .env with strong passwords)" -ForegroundColor White
Write-Host "  3. Run: .\launch-soc.ps1           (starts the SOC stack)" -ForegroundColor White
Write-Host "  4. Run: .\configure-lan.ps1        (share with teammates on LAN)" -ForegroundColor White
Write-Host ""
