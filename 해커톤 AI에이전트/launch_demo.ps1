# Demo launcher for the defect agent screens (used by the desktop shortcuts).
#   powershell -ExecutionPolicy Bypass -File launch_demo.ps1 -App dash   -> dashboard (http://localhost:8501/?demo=1)
#   powershell -ExecutionPolicy Bypass -File launch_demo.ps1 -App chat   -> chat      (http://localhost:8503/?demo=1)
# 1) starts Ollama if it is not running  2) starts the Streamlit server if it is not running
# 3) opens the browser in demo mode (?demo=1): the language picker + screen guide appear every time the page opens.
param([ValidateSet('dash', 'chat')][string]$App = 'dash', [switch]$NoBrowser)

$Root = $PSScriptRoot
$cfg = @{
    dash = @{ script = 'app.py';      port = 8501; name = 'Dashboard' }
    chat = @{ script = 'app_chat.py'; port = 8503; name = 'Chat' }
}[$App]
$py = Join-Path $Root '.venv\Scripts\python.exe'
$Host.UI.RawUI.WindowTitle = "Defect Agent - $($cfg.name) demo"

function Test-Up([string]$url) {
    try { Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 2 | Out-Null; return $true } catch { return $false }
}

Write-Host "Defect Agent - $($cfg.name) demo" -ForegroundColor Cyan

# 1. Ollama (Qwen)
if (Test-Up 'http://127.0.0.1:11434') {      # Ollama listens on IPv4 only; 'localhost' may try IPv6 first and time out
    Write-Host '[OK] Ollama is running'
} else {
    Write-Host 'Starting Ollama ...'
    try { Start-Process ollama -ArgumentList 'serve' -WindowStyle Hidden } catch { Write-Host '[!] Could not start Ollama - start it from the tray icon' -ForegroundColor Yellow }
}

# 2. Streamlit server
$health = "http://localhost:$($cfg.port)/_stcore/health"
if (Test-Up $health) {
    Write-Host "[OK] Server already running on port $($cfg.port)"
} else {
    if (-not (Test-Path $py)) { Write-Host "[X] Python venv not found: $py" -ForegroundColor Red; Read-Host 'Press Enter to close'; exit 1 }
    Write-Host "Starting server on port $($cfg.port) (first start takes 10-30 s) ..."
    Start-Process $py -WorkingDirectory $Root -WindowStyle Minimized -ArgumentList @(
        '-m', 'streamlit', 'run', $cfg.script, '--server.port', "$($cfg.port)",
        '--server.headless', 'true', '--browser.gatherUsageStats', 'false')
    for ($i = 0; $i -lt 120 -and -not (Test-Up $health); $i++) { Start-Sleep -Seconds 1 }
    if (-not (Test-Up $health)) { Write-Host '[X] Server did not start' -ForegroundColor Red; Read-Host 'Press Enter to close'; exit 1 }
    Write-Host '[OK] Server ready'
}

# 3. Browser in demo mode
if ($NoBrowser) { Write-Host "Demo URL: http://localhost:$($cfg.port)/?demo=1"; exit 0 }
Start-Process "http://localhost:$($cfg.port)/?demo=1"
Write-Host 'Opened the browser. The server keeps running in the minimized window (close it to stop).'
Start-Sleep -Seconds 3
