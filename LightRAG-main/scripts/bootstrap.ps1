param(
  [switch]$InitEnv,
  [switch]$InstallWebUI,
  [switch]$BuildWebUI
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

if (-not (Test-Command "uv")) {
  throw "未找到 uv。请先安装 uv 后再运行： https://docs.astral.sh/uv/"
}

& uv sync --extra api

if ($InstallWebUI -or $BuildWebUI) {
  if (-not (Test-Command "bun")) {
    throw "未找到 bun。请先安装 bun 后再运行： https://bun.sh/"
  }

  Push-Location ".\lightrag_webui"
  try {
    & bun install --frozen-lockfile
    if ($BuildWebUI) {
      & bun run build
    }
  }
  finally {
    Pop-Location
  }
}
