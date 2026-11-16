# Starts Software Factory: installs dependencies on first run, builds the UI, and launches the local app.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

$venv = Join-Path $root "backend\.venv"
if (-not (Test-Path (Join-Path $venv "Scripts\python.exe"))) {
    Write-Host "Creating Python environment..."
    python -m venv $venv
    & (Join-Path $venv "Scripts\python.exe") -m pip install --quiet -e (Join-Path $root "backend[dev]")
}

$frontend = Join-Path $root "frontend"
if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "Installing UI dependencies..."
    npm --prefix $frontend install --silent
}
$dist = Join-Path $frontend "dist\index.html"
$newestSource = Get-ChildItem (Join-Path $frontend "src") -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not (Test-Path $dist) -or $newestSource.LastWriteTime -gt (Get-Item $dist).LastWriteTime) {
    Write-Host "Building UI..."
    npm --prefix $frontend run build --silent
}

Set-Location $root
& (Join-Path $venv "Scripts\python.exe") -m software_factory.main
