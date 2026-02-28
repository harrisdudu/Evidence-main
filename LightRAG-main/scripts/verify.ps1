param(
  [string]$BaseUrl = "http://localhost:9621",
  [int]$TimeoutSec = 10
)

$ErrorActionPreference = "Stop"

$healthUrl = ($BaseUrl.TrimEnd("/") + "/health")
$resp = Invoke-RestMethod -Method Get -Uri $healthUrl -TimeoutSec $TimeoutSec

if ($resp.status -ne "healthy") {
  throw "健康检查失败：$healthUrl 返回 status=$($resp.status)"
}

$uri = [Uri]$BaseUrl
$port = $uri.Port

$portInfo = $null
try {
  $portInfo = Get-NetTCPConnection -LocalPort $port -ErrorAction Stop | Select-Object -First 5
}
catch {
}

Write-Host ("OK: " + $healthUrl)
Write-Host ("webui_available=" + $resp.webui_available)
Write-Host ("auth_mode=" + $resp.auth_mode)
Write-Host ("port=" + $port)
if ($null -ne $portInfo) {
  Write-Host ("listening=" + ($portInfo | ForEach-Object { $_.State } | Select-Object -First 1))
}
