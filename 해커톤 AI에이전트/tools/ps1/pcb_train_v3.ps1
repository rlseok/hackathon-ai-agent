# pcb_v3 (pcb_v2 + PCB_Project v8) fine-tuning from the pcb_v2 best model
# usage: powershell -ExecutionPolicy Bypass -File .\train_v3.ps1
Set-Location $PSScriptRoot
$yolo = Join-Path $env:USERPROFILE '.venv\Scripts\yolo.exe'
$data = Join-Path $PSScriptRoot 'data\pcb_v3\data.yaml'
$init = Join-Path $PSScriptRoot 'runs\detect\runs\pcb_v2_yolo11s\weights\best.pt'
& $yolo detect train "model=$init" "data=$data" epochs=60 imgsz=640 batch=8 workers=2 device=0 "project=$PSScriptRoot\runs\train" name=pcb_v3_ft
