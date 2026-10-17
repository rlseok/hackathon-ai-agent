# pcb_agent prediction script (works from any current directory)
# usage: powershell -ExecutionPolicy Bypass -File .\predict.ps1 [image or folder] [conf]
param(
    [string]$Source = 'data\pcb_v2\images\test',
    [string]$Conf = '0.25'
)
Set-Location $PSScriptRoot
$yolo = Join-Path $env:USERPROFILE '.venv\Scripts\yolo.exe'
$model = Join-Path $PSScriptRoot 'runs\detect\runs\pcb_v2_yolo11s\weights\best.pt'
if (-not (Test-Path $Source)) {
    Write-Host "[ERROR] Path not found: $Source" -ForegroundColor Red
    Write-Host "Put your images in the 'samples' folder and run:  predict.ps1 samples"
    exit 1
}
$src = Resolve-Path $Source
if ((Test-Path $src -PathType Container) -and -not (Get-ChildItem $src -File -Include *.jpg,*.jpeg,*.png,*.bmp -Recurse)) {
    Write-Host "[ERROR] No images (jpg/png/bmp) in: $src" -ForegroundColor Red
    exit 1
}
& $yolo predict "model=$model" "source=$src" "conf=$Conf" save=True save_crop=True "project=$PSScriptRoot\runs\eval" name=predict exist_ok=True
