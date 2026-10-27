# capture-printwindow.ps1
# Captures a window's contents with PrintWindow(PW_RENDERFULLCONTENT), which
# works even when the window is covered by another application.
param(
  [Parameter(Mandatory=$true)][string]$Script,
  [Parameter(Mandatory=$true)][string]$Out,
  [int]$WaitSeconds = 60
)
$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName System.Drawing

if (-not ('PW' -as [type])) {
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class PW {
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr h, int x, int y, int cx, int cy, bool repaint);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
}
"@
}

Get-Process WindowsTerminal -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 800

$wt = 'C:\Users\killer-4087-2\AppData\Local\Microsoft\WindowsApps\wt.exe'
Start-Process -FilePath $wt -ArgumentList @('powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',$Script) | Out-Null

$wtProc = $null
for ($i = 0; $i -lt 45; $i++) {
  Start-Sleep -Milliseconds 600
  $wtProc = Get-Process WindowsTerminal -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
  if ($wtProc) { break }
}
if (-not $wtProc) { Write-Output '  window not found'; exit 1 }

$hwnd = $wtProc.MainWindowHandle
[void][PW]::MoveWindow($hwnd, 40, 40, 1240, 900, $true)
Start-Sleep -Milliseconds 500

$r = New-Object PW+RECT
[void][PW]::GetWindowRect($hwnd, [ref]$r)
$w = $r.Right - $r.Left
$h = $r.Bottom - $r.Top
Write-Output ('  window pid ' + $wtProc.Id + '  rect ' + $w + 'x' + $h)

Start-Sleep -Seconds $WaitSeconds

$bmp = New-Object System.Drawing.Bitmap($w, $h)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
$ok = [PW]::PrintWindow($hwnd, $hdc, 2)     # 2 = PW_RENDERFULLCONTENT
$g.ReleaseHdc($hdc)
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Output ('  PrintWindow=' + $ok + '  saved ' + $Out + ' (' + $w + 'x' + $h + ')')

Get-Process WindowsTerminal -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -like "*$Script*" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
