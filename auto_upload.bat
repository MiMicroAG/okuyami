@echo off
REM =====================================================
REM  Okuyami pipeline (phased restore: 1 LINE, 2 summary, 3 logs)
REM  Steps: scrape -> parse -> upload -> (LINE notify)
REM =====================================================
setlocal EnableExtensions EnableDelayedExpansion
pushd "%~dp0"
chcp 65001 >nul 2>&1
REM ---- Console UTF-8 強制 (PowerShell 親ホスト向け) ----
powershell -NoLogo -NoProfile -Command "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new()" >nul 2>&1
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

REM ---- Timestamp & IDs ----
for /f "usebackq delims=" %%T in (`python -c "from datetime import datetime;print(datetime.now().strftime('%%Y%%m%%d_%%H%%M%%S'))"`) do set RUN_TS=%%T
set RUN_ID=%RANDOM%%RANDOM%

REM ---- Flags (disable line) ----
set ARGS=%*
set DISABLE_LINE=
set FORCE_LINE=
set _TMP=%ARGS:--force-line=%
if not "%_TMP%"=="%ARGS%" set FORCE_LINE=1
set _TMP=%ARGS:--no-line=%
if not "%_TMP%"=="%ARGS%" set DISABLE_LINE=1
set _TMP=%ARGS:--skip-line=%
if not "%_TMP%"=="%ARGS%" set DISABLE_LINE=1
set _TMP=%ARGS:--no-notify=%
if not "%_TMP%"=="%ARGS%" set DISABLE_LINE=1
if defined FORCE_LINE set DISABLE_LINE=

echo === OKUYAMI PIPELINE START ===
echo RUN_ID: %RUN_ID%   TS: %RUN_TS%
echo CWD: %CD%
echo Args: %ARGS%
if defined DISABLE_LINE (
	echo LINE notify disabled by flag (use --force-line to override)
) else if defined FORCE_LINE (
	echo LINE notify FORCED ON
) else (
	echo LINE notify enabled (auto)
)
echo.

REM ---- Repo path ----
set GITHUB_PAGES_REPO=%~dp0okuyami-info
if not exist "%GITHUB_PAGES_REPO%" goto NO_REPO
echo Repo: %GITHUB_PAGES_REPO%
echo.

REM ---- Logs dir ----
if not exist logs mkdir logs >nul 2>&1
set SCRAPE_LOG=logs\scrape_%RUN_TS%.log
set PARSE_LOG=logs\parse_%RUN_TS%.log
set UPLOAD_LOG=logs\upload_%RUN_TS%.log

REM ---- STEP 1 SCRAPE ----
echo [1] SCRAPE
python selenium_okuyami_scraper.py --auto --prefer-today >"%SCRAPE_LOG%" 2>&1
set SCRAPE_RC=%ERRORLEVEL%
type "%SCRAPE_LOG%"
for /f "usebackq delims=" %%D in (`python -c "from datetime import datetime;print(datetime.now().strftime('%%Y%%m%%d'))"`) do set TODAY_COMPACT=%%D
set TODAY_FILE=okuyami_data\okuyami_%TODAY_COMPACT%.txt
if "%SCRAPE_RC%"=="0" goto SCRAPE_OK
if exist "%TODAY_FILE%" goto SCRAPE_WARN
echo ERROR: scrape failed rc=%SCRAPE_RC% and no fallback file.
goto FAIL
:SCRAPE_WARN
echo WARN: scrape failed rc=%SCRAPE_RC% but using existing %TODAY_FILE%
:SCRAPE_OK
echo DONE scrape rc=%SCRAPE_RC%
echo.

REM ---- STEP 2 PARSE (deprecated direct parse; expect external CSV already produced) ----
echo [2] PARSE (skipped: CSV生成は別プロセスで実施)
if not exist "%TODAY_FILE%" echo WARN: %TODAY_FILE% が存在しないため後続CSV生成不可
echo.

REM ---- STEP 3 UPLOAD ----
echo [3] UPLOAD
python upload_to_github_pages.py --repo "%GITHUB_PAGES_REPO%" --message "Auto-update %date% %time%" >"%UPLOAD_LOG%" 2>&1
set UPLOAD_RC=%ERRORLEVEL%
type "%UPLOAD_LOG%"
if not "%UPLOAD_RC%"=="0" goto FAIL_UPLOAD
echo DONE upload rc=%UPLOAD_RC%
echo.

REM ---- STEP 4 LINE (optional) ----
if defined DISABLE_LINE goto SKIP_LINE
REM 取得: token & to (空なら送信しない)
set LINE_TOKEN=
set LINE_TO=
for /f "usebackq delims=" %%L in (`python -c "import configparser,os;cfg=configparser.ConfigParser();p='config.ini';print((cfg.read(p,encoding='utf-8') and cfg.get('line_messaging','channel_access_token',fallback='').strip()) if os.path.exists(p) else '')"`) do set LINE_TOKEN=%%L
for /f "usebackq delims=" %%L in (`python -c "import configparser,os;cfg=configparser.ConfigParser();p='config.ini';print((cfg.read(p,encoding='utf-8') and cfg.get('line_messaging','to',fallback='').strip()) if os.path.exists(p) else '')"`) do set LINE_TO=%%L
if not defined LINE_TOKEN goto SKIP_LINE
if not defined LINE_TO goto SKIP_LINE
echo [4] LINE notify (entries=%ENTRY_COUNT%) -> sending...
python send_line_stats.py >"logs\\line_%RUN_TS%.log" 2>&1
if errorlevel 1 (
	echo WARN: LINE notify failed (non-fatal)
) else (
	echo DONE line notify
)
goto AFTER_LINE
:SKIP_LINE
echo [4] LINE notify skipped (no token/to or disabled)
:AFTER_LINE
echo.
goto SUCCESS

:NO_DATA
echo INFO: No data (rc=2). Finish.
if defined DISABLE_LINE goto END_NO_DATA
set LINE_TOKEN=
for /f "usebackq delims=" %%L in (`python -c "import configparser,os;cfg=configparser.ConfigParser();p='config.ini';print((cfg.read(p,encoding='utf-8') and cfg.get('line_messaging','channel_access_token',fallback='').strip()) if os.path.exists(p) else '')"`) do set LINE_TOKEN=%%L
if not defined LINE_TOKEN goto END_NO_DATA
echo LINE notify (no data)
python send_line_stats.py --notify-no-data >"logs\line_%RUN_TS%_nodata.log" 2>&1
if errorlevel 1 echo WARN: LINE no-data notify failed
goto END_NO_DATA

:FAIL_PARSE
echo ERROR: parse failed rc=%PARSE_RC%
goto FAIL

:FAIL_UPLOAD
echo ERROR: upload failed rc=%UPLOAD_RC%
goto FAIL

:NO_REPO
echo ERROR: repo not found %GITHUB_PAGES_REPO%
goto FAIL

:SUCCESS
echo === PIPELINE SUCCESS ===
echo Entries: %ENTRY_COUNT%
echo Logs: %SCRAPE_LOG% , %PARSE_LOG% , %UPLOAD_LOG%
goto END

:END_NO_DATA
echo === PIPELINE SUCCESS (NO DATA) ===
echo Logs: %SCRAPE_LOG% , %PARSE_LOG%
goto END

:FAIL
echo === PIPELINE FAILED ===
echo Logs so far:
echo   %SCRAPE_LOG%
echo   %PARSE_LOG%
echo   %UPLOAD_LOG%
exit /b 1

:END
popd
exit /b 0

