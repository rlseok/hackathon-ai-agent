# Demo launcher for the defect agent screens (used by the desktop shortcuts).
#   powershell -ExecutionPolicy Bypass -File launch_demo.ps1 -App dash   -> dashboard (http://localhost:8501/?demo=1)
#   powershell -ExecutionPolicy Bypass -File launch_demo.ps1 -App chat   -> chat      (http://localhost:8503/?demo=1)
#   powershell -ExecutionPolicy Bypass -File launch_demo.ps1 -App live [-Line pcb|phone|metal|mixed] -> live inspection (http://localhost:8505)
#                                                                            + video server (http://localhost:8506)
# 1) starts Ollama if it is not running  2) starts the Streamlit server if it is not running
# 3) opens the browser in demo mode (?demo=1): the language picker + screen guide appear every time the page opens.
#   -Llm qwen3-defect  -> report / chat model (sets DEFECT_LLM for servers started now; a server already running keeps its model)
param([ValidateSet('dash', 'chat', 'live')][string]$App = 'dash', [ValidateSet('pcb', 'phone', 'metal', 'mixed')][string]$Line = 'pcb', [switch]$NoBrowser,
      [string]$Llm = '')

$Root = $PSScriptRoot
$cfg = @{
    dash = @{ script = 'app.py';      port = 8501; name = 'Dashboard' }
    chat = @{ script = 'app_chat.py'; port = 8503; name = 'Chat' }
    live = @{ script = 'app_live.py'; port = 8505; name = 'Live inspection' }
}[$App]
$py = Join-Path $Root '.venv\Scripts\python.exe'
if ($Llm) { $env:DEFECT_LLM = $Llm }        # child processes (Streamlit, video server) inherit it
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

# 2a. Live inspection: the video server is the only process that opens the camera / video
if ($App -eq 'live') {
    if (Test-Up 'http://127.0.0.1:8506/state') {
        Write-Host '[OK] Video server already running on port 8506'
    } else {
        Write-Host 'Starting video server on port 8506 ...'
        New-Item -ItemType Directory -Force (Join-Path $Root 'outputs\live') | Out-Null
        Start-Process $py -WorkingDirectory $Root -WindowStyle Minimized -ArgumentList @('-m', 'live.server', '--port', '8506', '--line', $Line)
        for ($i = 0; $i -lt 60 -and -not (Test-Up 'http://127.0.0.1:8506/state'); $i++) { Start-Sleep -Seconds 1 }
        if (Test-Up 'http://127.0.0.1:8506/state') { Write-Host '[OK] Video server ready' } else { Write-Host '[!] Video server did not start' -ForegroundColor Yellow }
    }
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
$url = if ($App -eq 'live') { "http://localhost:$($cfg.port)/" } else { "http://localhost:$($cfg.port)/?demo=1" }
if ($NoBrowser) { Write-Host "Demo URL: $url"; exit 0 }
Start-Process $url
Write-Host 'Opened the browser. The server keeps running in the minimized window (close it to stop).'
Start-Sleep -Seconds 3
