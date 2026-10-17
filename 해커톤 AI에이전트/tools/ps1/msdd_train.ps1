# msdd segmentation training script (works from any current directory)
# usage: powershell -ExecutionPolicy Bypass -File .\train.ps1
Set-Location $PSScriptRoot
$yolo = Join-Path $env:USERPROFILE '.venv\Scripts\yolo.exe'
$data = Join-Path $PSScriptRoot 'data\msdd_v1\data.yaml'
& $yolo segment train model=yolo11s-seg.pt "data=$data" epochs=150 imgsz=512 batch=8 workers=2 device=0 patience=40 "project=$PSScriptRoot\runs\train" name=msdd_v1_yolo11s_seg
