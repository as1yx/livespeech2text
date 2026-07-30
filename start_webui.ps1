# LiveSpeech2Text Web UI Launcher
# - spinner animation while model loads
# - opens browser when port 7860 is listening
# - shows live log of webui.log

$ErrorActionPreference = "Continue"
$ProjectRoot = $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

$spin = @('|', '/', '-', '\')
$script:spin_i = 0

function Spinner-Line($label) {
    $script:spin_i += 1
    $ch = $spin[$script:spin_i % 4]
    return "[$ch] $label"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  LiveSpeech2Text - Web UI" -ForegroundColor Cyan
Write-Host "  http://localhost:7860" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check venv
$VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$LogFile = Join-Path $ProjectRoot "webui.log"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[ERROR] venv not found at: $ProjectRoot\venv" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# 2. Check if 7860 already in use
$PortInUse = Get-NetTCPConnection -LocalPort 7860 -State Listen -ErrorAction SilentlyContinue
if ($PortInUse) {
    Write-Host "[!] Port 7860 already in use. Opening browser..." -ForegroundColor Yellow
    Start-Process "http://localhost:7860"
    Read-Host "Press Enter to exit"
    exit 0
}

# 3. Start Python in background using ProcessStartInfo (allows merged stdout/stderr)
Write-Host "[1/3] Starting Python in background..." -ForegroundColor Green
if (Test-Path $LogFile) { Remove-Item $LogFile -Force }

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $VenvPython
$psi.Arguments = "`"$($ProjectRoot)\web_ui.py`""
$psi.WorkingDirectory = $ProjectRoot
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.CreateNoWindow = $true
$psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
$psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
$psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8"

$proc = [System.Diagnostics.Process]::Start($psi)
$script:proc = $proc

# Hook output to write into log file
$proc.add_OutputDataReceived({
    if ($_.Data) { Add-Content -Path $LogFile -Value $_.Data -Encoding UTF8 }
})
$proc.add_ErrorDataReceived({
    if ($_.Data) { Add-Content -Path $LogFile -Value "[ERR] $($_.Data)" -Encoding UTF8 }
})
$proc.BeginOutputReadLine()
$proc.BeginErrorReadLine()

Write-Host "      PID: $($proc.Id)" -ForegroundColor DarkGray
Write-Host "      Log: $LogFile" -ForegroundColor DarkGray

# 4. Spinner + port watch
Write-Host "[2/3] Loading model (first time: 30-60s, second time: 5-10s)..." -ForegroundColor Green
$startTime = Get-Date

while (-not $proc.HasExited -and -not (Get-NetTCPConnection -LocalPort 7860 -State Listen -ErrorAction SilentlyContinue)) {
    $elapsed = [int]((Get-Date) - $startTime).TotalSeconds
    $label = "Loading model and starting service... ({0}s)" -f $elapsed
    Write-Host "`r$(Spinner-Line $label)            " -NoNewline -ForegroundColor Yellow
    Start-Sleep -Milliseconds 250
}

if ($proc.HasExited) {
    Write-Host ""
    Write-Host "[ERROR] Python exited unexpectedly. Last log lines:" -ForegroundColor Red
    if (Test-Path $LogFile) {
        Get-Content $LogFile -Tail 30
    }
    Read-Host "Press Enter to exit"
    exit 1
}

$loadTime = [int]((Get-Date) - $startTime).TotalSeconds
Write-Host ""
Write-Host "[3/3] Service is ready! (loaded in ${loadTime}s)" -ForegroundColor Green
Start-Process "http://localhost:7860"

# 5. Live log
Write-Host ""
Write-Host "=== Live log (close this window or Ctrl+C to stop) ===" -ForegroundColor Cyan
Write-Host ""

try {
    Get-Content $LogFile -Wait -Tail 20
} finally {
    if (-not $proc.HasExited) {
        Write-Host ""
        Write-Host "[!] Stopping service..." -ForegroundColor Yellow
        $proc | Stop-Process -Force
    }
}
