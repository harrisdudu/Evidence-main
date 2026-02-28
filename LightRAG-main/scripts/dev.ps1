param(
  [switch]$InitEnv,
  [int]$BackendPort = 9621,
  [int]$WebuiPort = 5173
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

& "$PSScriptRoot\bootstrap.ps1" -InitEnv:$InitEnv -InstallWebUI

$backend = Start-Process -FilePath "uv" -ArgumentList @(
  "run",
  "lightrag-server",
  "--port",
  "$BackendPort"
) -WorkingDirectory $repoRoot -NoNewWindow -PassThru

$webuiDir = Join-Path $repoRoot "lightrag_webui"
$frontend = Start-Process -FilePath "bun" -ArgumentList @(
  "run",
  "dev",
  "--port",
  "$WebuiPort"
) -WorkingDirectory $webuiDir -NoNewWindow -PassThru

try {
  Write-Host "WebUI: http://localhost:$WebuiPort/webui/"
  Write-Host "API:   http://localhost:$BackendPort"
  Write-Host "Health: http://localhost:$BackendPort/health"
  Wait-Process -Id @($backend.Id, $frontend.Id)
}
finally {
  foreach ($p in @($frontend, $backend)) {
    if ($null -ne $p -and -not $p.HasExited) {
      Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    }
  }
}
