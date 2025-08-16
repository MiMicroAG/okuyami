$ErrorActionPreference='Stop'
$dates = 4..16 | ForEach-Object { '2025-08-{0:00}' -f $_ }
foreach($d in $dates){
  $fn = 'okuyami_data/okuyami_' + ($d -replace '-','') + '.txt'
  if(Test-Path $fn){
    Write-Host "=== PROCESS $d ===" -ForegroundColor Cyan
    python parse_and_format_obituary.py --file $fn
  } else {
    Write-Host "MISSING $fn" -ForegroundColor Yellow
  }
}
Write-Host 'ALL DONE'
