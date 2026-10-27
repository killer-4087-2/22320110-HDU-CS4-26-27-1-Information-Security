# capture-wt2.ps1 - run a script in Windows Terminal and capture its window.
# Uses WScript.Shell AppActivate because SetForegroundWindow is unreliable here.
param(
  [Parameter(Mandatory=$true)][string]$Script,
  [Parameter(Mandatory=$true)][string]$Out,
  [int]$WaitSeconds = 50
)
$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName System.Drawing

if (-not ('CapW' -as [type])) {
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class CapW {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr SetActiveWindow(IntPtr h);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
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
Write-Output ('  window ready, pid ' + $wtProc.Id)

Start-Sleep -Seconds $WaitSeconds

# bring it to the front - three different mechanisms, because any one may fail
$hwnd = $wtProc.MainWindowHandle
[void][CapW]::ShowWindow($hwnd, 9)
[void][CapW]::SetWindowPos($hwnd, [IntPtr](-1), 40, 40, 1240, 880, 0x40)
try {
  $ws = New-Object -ComObject WScript.Shell
  [void]$ws.AppActivate($wtProc.Id)
} catch { }
Start-Sleep -Milliseconds 300
[void][CapW]::BringWindowToTop($hwnd)
[void][CapW]::SetActiveWindow($hwnd)
[void][CapW]::SetForegroundWindow($hwnd)
Start-Sleep -Seconds 2

$r = New-Object CapW+RECT
[void][CapW]::GetWindowRect($hwnd, [ref]$r)
$w = $r.Right - $r.Left
$h = $r.Bottom - $r.Top
$bmp = New-Object System.Drawing.Bitmap($w, $h)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($r.Left, $r.Top, 0, 0, (New-Object System.Drawing.Size($w, $h)))
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Output ('  saved ' + $Out + '  (' + $w + 'x' + $h + ')')

Get-Process WindowsTerminal -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -like "*$Script*" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
