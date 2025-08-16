@echo off
setlocal enabledelayedexpansion
REM Bulk generation 2025-08-04 .. 2025-08-13
set DATES=2025-08-04 2025-08-05 2025-08-06 2025-08-07 2025-08-08 2025-08-09 2025-08-10 2025-08-11 2025-08-12 2025-08-13

for %%D in (%DATES%) do call :PROC %%D
echo ==================================================
echo ALL DONE
goto :EOF

:PROC
set CUR=%1
echo ==================================================
echo [%CUR%] SCRAPE START
python selenium_okuyami_scraper.py --date %CUR%
if errorlevel 1 (
  echo [%CUR%] SCRAPE FAILED (skip)
  goto :EOF
)
set CURNO=%CUR:-=%
set TXT=okuyami_data\okuyami_%CURNO%.txt
if not exist "%TXT%" (
  echo [%CUR%] TXT NOT FOUND (%TXT%)
  goto :EOF
)
echo [%CUR%] PARSE->MD START
python parse_and_format_obituary.py --file "%TXT%"
if errorlevel 1 (
  echo [%CUR%] PARSE FAILED
) else (
  echo [%CUR%] DONE
)
goto :EOF

echo ==================================================
echo 全日処理終了
endlocal
