@echo off
setlocal enabledelayedexpansion
REM Parse already-downloaded obituary text files (2025-08-04 .. 2025-08-13) into CSV/MD
set DATES=2025-08-04 2025-08-05 2025-08-06 2025-08-07 2025-08-08 2025-08-09 2025-08-10 2025-08-11 2025-08-12 2025-08-13

for %%D in (%DATES%) do call :PARSE_ONE %%D
echo ================================================
echo ALL PARSE DONE
goto :EOF

:PARSE_ONE
set CUR=%1
set CURNO=%CUR:-=%
set TXT=okuyami_data\okuyami_%CURNO%.txt
if not exist "%TXT%" (
  echo [%CUR%] MISSING %TXT%
  goto :EOF
)
echo ------------------------------------------------
echo [%CUR%] PARSE START (%TXT%)
python parse_and_format_obituary.py --file "%TXT%"
if errorlevel 1 (
  echo [%CUR%] PARSE FAIL
) else (
  echo [%CUR%] PARSE OK
)
goto :EOF
