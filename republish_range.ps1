param(
  [string]$Pattern = 'okuyami_output/okuyami_2025080*_parsed_20250816_1130*.md'
)
$ErrorActionPreference='Stop'
# UTF-8 環境初期化 (git 文字化け防止)
try {
  chcp 65001 > $null
  $env:LANG = 'ja_JP.UTF-8'
  [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
  # 対象リポジトリ (固定パス) に対して設定
  $repo = Resolve-Path './okuyami-info'
  git -C $repo i18n.commitEncoding utf-8 | Out-Null
  git -C $repo i18n.logOutputEncoding utf-8 | Out-Null
  git -C $repo config core.quotepath false | Out-Null
} catch {}

# ファイル列挙 (デフォルトは 08/04 〜 08/16 新生成一式)
$files = Get-ChildItem -Path $Pattern -File | Sort-Object Name | ForEach-Object { $_.FullName.Replace('\','/') }
if(-not $files){ Write-Host "該当ファイルなし: $Pattern" -ForegroundColor Yellow; exit 0 }
Write-Host "対象ファイル数: $($files.Count)" -ForegroundColor Cyan

foreach($p in $files){
  if(Test-Path $p){
    if($p -match 'okuyami_(\d{8})_'){
      $d = [datetime]::ParseExact($matches[1],'yyyyMMdd',$null).ToString('yyyy-MM-dd')
      $msg = "再投稿 $d お悔やみ情報"
      Write-Host "POST $d => $p" -ForegroundColor Cyan
      python upload_to_github_pages.py --repo ./okuyami-info --file $p --date $d --message $msg
      if($LASTEXITCODE -ne 0){ Write-Host "FAIL $d" -ForegroundColor Red }
      Start-Sleep -Milliseconds 300
    }
  } else {
    Write-Host "MISSING $p" -ForegroundColor Yellow
  }
}
Write-Host '完了 (差分なしファイルはスキップされた可能性があります)' -ForegroundColor Green
