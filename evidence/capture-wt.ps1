# Run a demo script inside a real Windows Terminal window and capture it.
# ASCII-only on purpose: PowerShell 5.1 reads BOM-less files as ANSI.
param(
  [Parameter(Mandatory=$true)][string]$Script,
  [Parameter(Mandatory=$true)][string]$Out,
  [int]$WaitSeconds = 25
)
$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName System.Drawing

if (-not ('CapWt' -as [type])) {
Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class CapWt {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
}
"@
}

# close any terminal from previous runs
Get-Process WindowsTerminal -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 800

$before = @(Get-Process WindowsTerminal -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)

$wt = 'C:\Users\killer-4087-2\AppData\Local\Microsoft\WindowsApps\wt.exe'
Start-Process -FilePath $wt -ArgumentList @(
  'powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',$Script
) | Out-Null
Write-Output "  launched via Windows Terminal"

$hwnd = [IntPtr]::Zero
for ($i = 0; $i -lt 45; $i++) {
  Start-Sleep -Milliseconds 600
  $p = Get-Process WindowsTerminal -ErrorAction SilentlyContinue |
       Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
  if ($p) { $hwnd = $p.MainWindowHandle; break }
}
if ($hwnd -eq [IntPtr]::Zero) {
  Write-Output "  window not found"
  exit 1
}
Write-Output ("  window ready HWND={0}, running script..." -f $hwnd)

Start-Sleep -Seconds $WaitSeconds

[void][CapWt]::ShowWindow($hwnd, 9)
[void][CapWt]::SetWindowPos($hwnd, [IntPtr](-1), 40, 40, 1220, 860, 0x40)
[void][CapWt]::SetForegroundWindow($hwnd)
Start-Sleep -Milliseconds 1800

$r = New-Object CapWt+RECT
[void][CapWt]::GetWindowRect($hwnd, [ref]$r)
$w = $r.Right - $r.Left
$h = $r.Bottom - $r.Top
$bmp = New-Object System.Drawing.Bitmap($w, $h)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($r.Left, $r.Top, 0, 0, (New-Object System.Drawing.Size($w, $h)))
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Output ("  saved {0}  ({1}x{2})" -f $Out, $w, $h)

# clean up: the terminal and the child powershell it spawned
Get-Process WindowsTerminal -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -like "*$Script*" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
