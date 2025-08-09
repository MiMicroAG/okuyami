# PowerShell wrapper to run auto_upload.bat reliably from any shell/location
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$bat = Join-Path $here 'auto_upload.bat'
if (-not (Test-Path $bat)) {
  Write-Error "Batch file not found: $bat"
  exit 1
}
# Run via cmd to ensure proper BAT semantics
& cmd.exe /c "\"$bat\""
exit $LASTEXITCODE
