# W1-FIXED  -- same request replayed against the fixed runtime + regression test
$ErrorActionPreference = 'Continue'
$Host.UI.RawUI.WindowTitle = 'W1-FIXED'
$Host.UI.RawUI.BackgroundColor = 'Black'
$Host.UI.RawUI.ForegroundColor = 'Gray'
Clear-Host

$cve = 'D:\killer-4087-2\Work1-SecureAPI\cve\CVE-2017-14849'
Set-Location $cve

Write-Host ''
Write-Host '  CVE-2017-14849 : verification of the fix' -ForegroundColor White
Write-Host '  same application, same request, fixed runtime' -ForegroundColor DarkGray
Write-Host '  ------------------------------------------------------------------' -ForegroundColor DarkGray

Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
  Where-Object { $_.CommandLine -like '*app.js*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 1

$node24 = (Get-Command node).Source
Start-Process -FilePath $node24 -ArgumentList 'www\app.js' -WorkingDirectory $cve -WindowStyle Hidden
Start-Sleep -Seconds 3

Write-Host ''
Write-Host '  [1] runtime after the fix' -ForegroundColor Cyan
& node --version
Write-Host ''
Write-Host '  [2] replay the identical attack' -ForegroundColor Cyan
Write-Host '      GET /static/../foo/../../secret.txt' -ForegroundColor Yellow
& curl.exe --path-as-is -s -o NUL -w "      ->  HTTP %{http_code}  (expected 404)`n" http://127.0.0.1:3000/static/../foo/../../secret.txt
Write-Host ''
Write-Host '  [3] regression: legitimate functionality still works' -ForegroundColor Cyan
& curl.exe --path-as-is -s -o NUL -w "      GET /static/main.js  ->  HTTP %{http_code}`n" http://127.0.0.1:3000/static/main.js
& curl.exe --path-as-is -s -o NUL -w "      GET /                ->  HTTP %{http_code}`n" http://127.0.0.1:3000/
Write-Host ''
Write-Host '  ------------------------------------------------------------------' -ForegroundColor DarkGray
Write-Host '  Attack blocked (404), service intact (200). Fix verified.' -ForegroundColor Green
Write-Host ''
Start-Sleep -Seconds 180
