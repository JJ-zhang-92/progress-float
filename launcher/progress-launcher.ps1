# Progress Float Launcher
# Starts the server (if not running) and opens the floating ball widget.
# Usage: .\progress-launcher.ps1

param(
  [int]$Port = 19822
)

$url = "http://127.0.0.1:${Port}"
$cacheDir = "C:\.opencode\cache"
$serverScript = "C:\.opencode\.opencode\plugins\progress-server.js"
$widgetScript = "C:\.opencode\progress-float.pyw"

# Ensure cache dir exists
if (-not (Test-Path -LiteralPath $cacheDir)) {
  New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null
}

# Start server if not running
try {
  $null = Invoke-WebRequest -Uri "$url/state" -UseBasicParsing -TimeoutSec 2
  Write-Host "Server already running at $url"
} catch {
  Write-Host "Starting progress server..."
  Start-Process -FilePath "node" -ArgumentList $serverScript,$Port,$cacheDir -WindowStyle Hidden
  Start-Sleep -Seconds 1
  try {
    $null = Invoke-WebRequest -Uri "$url/state" -UseBasicParsing -TimeoutSec 2
    Write-Host "Server started at $url"
  } catch {
    Write-Host "ERROR: Could not start server. Check that Node.js is installed."
    Write-Host "To install: winget install OpenJS.NodeJS"
    exit 1
  }
}

# Launch floating ball widget
Write-Host "Launching floating ball..."
Start-Process -FilePath "pythonw" -ArgumentList $widgetScript

Write-Host "Floating ball launched!"
Write-Host ""
Write-Host "  ●  Gray = idle  |  Green pulsing = working"
Write-Host "  ●  Red badge = active tool count"
Write-Host "  ●  Click ball = expand detail panel"
Write-Host "  ●  Drag ball to reposition"
Write-Host "  ●  Close by clicking [X] or stop pythonw process"
