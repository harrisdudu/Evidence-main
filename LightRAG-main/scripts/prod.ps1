param(
  [switch]$InitEnv
)

$ErrorActionPreference = "Stop"

function Test-Command {
  param([Parameter(Mandatory = $true)][string]$Name)
  return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

if ($InitEnv -and -not (Test-Path ".\.env")) {
  Copy-Item ".\env.example" ".\.env"
}

if (-not (Test-Command "docker")) {
  throw "未找到 docker。生产环境建议使用 Docker Desktop 或在 Linux 服务器安装 Docker。"
}

& docker compose up
