# pcb_agent training script (works from any current directory)
# usage: powershell -ExecutionPolicy Bypass -File .\train.ps1
Set-Location $PSScriptRoot
$yolo = Join-Path $env:USERPROFILE '.venv\Scripts\yolo.exe'
$data = Join-Path $PSScriptRoot 'data\pcb_v2\data.yaml'
& $yolo detect train model=yolo11s.pt "data=$data" epochs=100 imgsz=640 batch=8 workers=2 device=0 project=runs name=pcb_v2_yolo11s
