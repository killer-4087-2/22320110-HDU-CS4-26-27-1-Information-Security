# Launch a demo script in a real console window and capture that window.
# ASCII-only on purpose: PowerShell 5.1 reads BOM-less files as ANSI.
param(
  [Parameter(Mandatory=$true)][string]$Script,
  [Parameter(Mandatory=$true)][string]$Out,
  [int]$WaitSeconds = 25
)
$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName System.Drawing

if (-not ('CapWin2' -as [type])) {
Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class CapWin2 {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }

  public static IntPtr FindByPid(uint target) {
    IntPtr found = IntPtr.Zero;
    EnumWindows(delegate(IntPtr h, IntPtr l) {
      uint pid; GetWindowThreadProcessId(h, out pid);
      if (pid == target && IsWindowVisible(h)) {
        StringBuilder sb = new StringBuilder(512);
        GetWindowText(h, sb, 512);
        if (sb.Length > 0) { found = h; return false; }
      }
      return true;
    }, IntPtr.Zero);
    return found;
  }
}
"@
}

$proc = Start-Process -FilePath 'powershell.exe' `
  -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',$Script -PassThru
Write-Output ("  started PID {0}, waiting for its window..." -f $proc.Id)

$hwnd = [IntPtr]::Zero
for ($i = 0; $i -lt 45; $i++) {
  Start-Sleep -Milliseconds 600
  $hwnd = [CapWin2]::FindByPid([uint32]$proc.Id)
  if ($hwnd -ne [IntPtr]::Zero) { break }
  if ($proc.HasExited) { break }
}

if ($hwnd -eq [IntPtr]::Zero) {
  Write-Output "  window not found"
  if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
  exit 1
}

$sb = New-Object System.Text.StringBuilder 512
[void][CapWin2]::GetWindowText($hwnd, $sb, 512)
Write-Output ("  window ready: '{0}', running..." -f $sb.ToString())

Start-Sleep -Seconds $WaitSeconds

[void][CapWin2]::ShowWindow($hwnd, 9)
[void][CapWin2]::SetWindowPos($hwnd, [IntPtr](-1), 60, 60, 1180, 820, 0x40)
[void][CapWin2]::SetForegroundWindow($hwnd)
Start-Sleep -Milliseconds 1500

$r = New-Object CapWin2+RECT
[void][CapWin2]::GetWindowRect($hwnd, [ref]$r)
$w = $r.Right - $r.Left
$h = $r.Bottom - $r.Top
$bmp = New-Object System.Drawing.Bitmap($w, $h)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($r.Left, $r.Top, 0, 0, (New-Object System.Drawing.Size($w, $h)))
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Output ("  saved {0}  ({1}x{2})" -f $Out, $w, $h)

if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
