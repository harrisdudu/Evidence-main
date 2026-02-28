param(
  [switch]$InitEnv,
  [int]$Port = 9621,
  [string]$BindHost = "0.0.0.0"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

& "$PSScriptRoot\bootstrap.ps1" -InitEnv:$InitEnv -BuildWebUI

& uv run lightrag-server --host $BindHost --port $Port
