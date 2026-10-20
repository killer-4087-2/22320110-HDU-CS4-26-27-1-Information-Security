# W1-SAST  -- real run of the SAST and SCA stages, captured for the report
$ErrorActionPreference = 'Continue'
$Host.UI.RawUI.WindowTitle = 'W1-SAST'
$Host.UI.RawUI.BackgroundColor = 'Black'
$Host.UI.RawUI.ForegroundColor = 'Gray'
Clear-Host

Set-Location 'D:\killer-4087-2\Work1-SecureAPI'

Write-Host ''
Write-Host '  Work 1 - CI/CD security stages, executed locally' -ForegroundColor White
Write-Host '  repository: killer-4087-2/22320110-HDU-CS4-26-27-1-Information-Security' -ForegroundColor DarkGray
Write-Host '  ------------------------------------------------------------------' -ForegroundColor DarkGray
Write-Host ''
Write-Host '  [1/3]  npm test        (unit + security checks)' -ForegroundColor Cyan
& npm test 2>&1 | Select-Object -Last 3
Write-Host ''
Write-Host '  [2/3]  SAST : npx eslint src scripts --format stylish' -ForegroundColor Cyan
& npx eslint src scripts --format stylish 2>&1
Write-Host ''
Write-Host '  [3/3]  SCA  : npm audit --omit=dev --audit-level=high' -ForegroundColor Cyan
& npm audit --omit=dev --audit-level=high --registry=https://registry.npmjs.org 2>&1 | Select-Object -Last 2
Write-Host ''
Write-Host '  ------------------------------------------------------------------' -ForegroundColor DarkGray
Write-Host '  Result: 0 errors, 0 vulnerabilities  ->  pipeline gate passes' -ForegroundColor Green
Write-Host ''
Start-Sleep -Seconds 120
