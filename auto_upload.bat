@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM 作業ディレクトリをこのバッチファイルの場所に固定
pushd "%~dp0"
chcp 65001 >nul 2>&1
cls
REM 引数処理: 非対話モード/LINE無効化（Task Schedulerや無通知運用向け）
set "ALL_ARGS=%*"
REM 非対話モード検出（--ci or --noninteractive が含まれる場合）
for %%K in ("--ci" "--noninteractive") do (
    call set "_TMP=!ALL_ARGS:%%~K=!"
    if not "!_TMP!"=="%ALL_ARGS%" set "OKUYAMI_NONINTERACTIVE=1"
)
REM LINE通知無効化（--no-line, --no-notify, --skip-line のいずれか）
for %%K in ("--no-line" "--no-notify" "--skip-line") do (
    call set "_TMP=!ALL_ARGS:%%~K=!"
    if not "!_TMP!"=="%ALL_ARGS%" set "OKUYAMI_DISABLE_LINE=1"
)
echo.
echo ==========================================
echo   お悔やみ情報 完全自動取得・アップローダー  
echo ==========================================
echo.

REM GitHub Pagesリポジトリのパスを設定（優先順: 環境変数 -> バッチ隣 -> OneDrive -> USERPROFILE\OneDrive）
if not defined GITHUB_PAGES_REPO (
    REM 1) バッチと同階層の okuyami-info を優先
    set "_CAND1=%~dp0okuyami-info"
    if exist "!_CAND1!\.git" (
        set "GITHUB_PAGES_REPO=!_CAND1!"
    ) else (
        if defined OneDrive (
            REM 2) OneDrive 直下（従来の既定）
            set "_CAND2=%OneDrive%\Develop\okuyami\okuyami-info"
            if exist "!_CAND2!\.git" (
                set "GITHUB_PAGES_REPO=!_CAND2!"
            ) else (
                REM 3) USERPROFILE\OneDrive 経由
                set "_CAND3=%USERPROFILE%\OneDrive\Develop\okuyami\okuyami-info"
                if exist "!_CAND3!\.git" (
                    set "GITHUB_PAGES_REPO=!_CAND3!"
                ) else (
                    set "GITHUB_PAGES_REPO=!_CAND2!"  REM 最後に一応セット
                )
            )
        ) else (
            set "GITHUB_PAGES_REPO=%USERPROFILE%\OneDrive\Develop\okuyami\okuyami-info"
        )
    )
)

REM LINE Messaging API 設定（--no-line 等がある場合は完全無効化）
if defined OKUYAMI_DISABLE_LINE (
    echo LINE notifications disabled by option.
) else (
    REM set "LINE_MESSAGING_CHANNEL_ACCESS_TOKEN=..."
    REM set "LINE_MESSAGING_TO=Uxxxxxxxxxxxxxxx,Gyyyyyyyyyyyyyyy"
    if not defined LINE_MESSAGING_CHANNEL_ACCESS_TOKEN (
        for /f "usebackq delims=" %%T in (`python -c "import configparser,os;cfg=configparser.ConfigParser();p='config.ini';print((cfg.read(p,encoding='utf-8') and cfg.get('line_messaging','channel_access_token',fallback='').strip()) if os.path.exists(p) else '')"`) do set "LINE_MESSAGING_CHANNEL_ACCESS_TOKEN=%%T"
    )
    if not defined LINE_MESSAGING_TO (
        for /f "usebackq delims=" %%T in (`python -c "import configparser,os;cfg=configparser.ConfigParser();p='config.ini';print((cfg.read(p,encoding='utf-8') and cfg.get('line_messaging','to',fallback='').strip()) if os.path.exists(p) else '')"`) do set "LINE_MESSAGING_TO=%%T"
    )
    if defined LINE_MESSAGING_CHANNEL_ACCESS_TOKEN (
        echo LINE Messaging token detected - will use Messaging API
    ) else (
        echo LINE tokens not set. Stats will NOT be sent to LINE.
    )
)

REM リポジトリパスの存在確認
REM 表示用にユーザー名を含むパスを環境変数表記へ置換
set "DISPLAY_REPO=%GITHUB_PAGES_REPO%"
if defined OneDrive set "DISPLAY_REPO=!DISPLAY_REPO:%OneDrive%=%%OneDrive%%!"
if defined USERPROFILE set "DISPLAY_REPO=!DISPLAY_REPO:%USERPROFILE%=%%USERPROFILE%%!"

if not exist "%GITHUB_PAGES_REPO%" (
    echo Error: GitHub Pages repository not found
    echo Path: !DISPLAY_REPO!
    echo.
    echo Please set correct path at the beginning of this batch file.
    if not defined OKUYAMI_NONINTERACTIVE pause
    exit /b 1
)

echo GitHub Pages Repository: !DISPLAY_REPO!
echo.

REM 実行前の準備: 既存プロセスのクリーンアップ
echo Preparing execution...
echo    - Cleaning up existing WebDriver processes (chromedriver only)
taskkill /F /IM chromedriver.exe >nul 2>&1
REM 既存のChrome本体(chrome.exe)は終了しない（ユーザーの作業を中断しないため）
REM 強制終了が必要な場合のみ、環境変数 OKUYAMI_FORCE_KILL_CHROME=1 を設定
if /I "%OKUYAMI_FORCE_KILL_CHROME%"=="1" (
    echo    - Forcing chrome.exe termination due to OKUYAMI_FORCE_KILL_CHROME=1
    taskkill /F /IM chrome.exe >nul 2>&1
)
timeout /t 3 >nul
echo    ✓ Cleanup completed
echo.

REM 1. ネットからお悔やみ情報を取得
echo 1. Fetching obituary information from web...
echo    - Accessing Yamanashi Nichinichi Shimbun
echo    - Login authentication
echo    - Scraping obituary information
echo.

python selenium_okuyami_scraper.py --auto --prefer-today
set "SCRAPE_RC=%ERRORLEVEL%"
REM 取得失敗時でも本日分のローカルファイルがあれば続行
for /f "usebackq delims=" %%D in (`python -c "from datetime import datetime;print(datetime.now().strftime('%%Y%%m%%d'))"`) do set "TODAY_COMPACT=%%D"
set "TODAY_FILE=okuyami_data\okuyami_!TODAY_COMPACT!.txt"
if not "%SCRAPE_RC%"=="0" (
    if exist "!TODAY_FILE!" (
        echo.
        echo Warning: Web fetch failed, but found existing local data for today - proceeding: !TODAY_FILE!
        set "SCRAPE_RC=0"
    ) else (
        echo.
        echo Error: Failed to fetch obituary information (today not found or runtime error)
        if defined OKUYAMI_DISABLE_LINE (
            echo    - LINE notification disabled; skipping no-data message
        ) else (
            if defined LINE_MESSAGING_CHANNEL_ACCESS_TOKEN (
                echo    - Will notify LINE: No data for today
                python send_line_stats.py --notify-no-data
            ) else (
                echo    - LINE token not set; skipping notification
            )
        )
        echo.
        if not defined OKUYAMI_NONINTERACTIVE pause
        exit /b 1
    )
)
echo.
echo    ✓ Obituary information fetch completed
echo.

REM 2. 取得したデータを解析・フォーマット
echo 2. Analyzing and formatting obituary data...
echo    - Structuring text data
echo    - Generating CSV and Markdown files
echo    - Applying priority sorting (NEC → Chuo-shi → Others)

python parse_and_format_obituary.py --auto
set "PARSE_RC=%ERRORLEVEL%"
if "%PARSE_RC%"=="2" (
    echo No obituary entries parsed for today.
    if defined OKUYAMI_DISABLE_LINE (
        echo    - LINE notification disabled; skipping no-data message
    ) else if defined LINE_MESSAGING_CHANNEL_ACCESS_TOKEN (
        echo    - Notifying LINE (no obituary data)
        python send_line_stats.py --notify-no-data
    ) else (
        echo    - LINE token not set; skipping notification
    )
    echo.
    echo Process finished (no data). Exiting gracefully.
    if not defined OKUYAMI_NONINTERACTIVE pause
    exit /b 0
) else if not "%PARSE_RC%"=="0" (
    echo Error: Failed to analyze and format obituary data (rc=%PARSE_RC%)
    if not defined OKUYAMI_NONINTERACTIVE pause
    exit /b 1
)

echo    ✓ Obituary data analysis and formatting completed
echo.

REM 3. GitHub Pagesにアップロード
echo 3. Uploading to GitHub Pages...
echo    - Converting to Jekyll format
echo    - Git commit and push

python upload_to_github_pages.py --repo "%GITHUB_PAGES_REPO%" --message "Auto-update obituary info (%date% %time%)"
if errorlevel 1 (
    echo Error: Failed to upload to GitHub Pages
    echo    - Check Git authentication
    echo    - Check repository path
    if not defined OKUYAMI_NONINTERACTIVE pause
    exit /b 1
)

echo    ✓ GitHub Pages upload completed
echo.

REM 4. 公開待ち後のLINE通知（無効化時はスキップ）
if defined OKUYAMI_DISABLE_LINE (
    echo Skipping LINE notification as requested.
) else (
    echo 4. Waiting ~120 seconds for site publish before sending LINE notification...
    timeout /t 120 >nul
    if defined LINE_MESSAGING_CHANNEL_ACCESS_TOKEN (
        python send_line_stats.py
        if errorlevel 1 (
            echo Warning: Failed to send LINE notification (non-fatal)
        )
    )
    echo.
)

REM 4. 完了メッセージと結果表示
echo ==========================================
echo   All processes completed successfully!
echo ==========================================
echo.
echo Executed processes:
echo   1. ✓ Fetched obituary information from web
echo   2. ✓ Analyzed, structured and formatted data
echo   3. ✓ Automatically uploaded to GitHub Pages
if not defined OKUYAMI_DISABLE_LINE echo   4. ✓ (After delay) Sent LINE notification
echo.
echo Updates will be reflected on GitHub Pages in a few minutes.
echo Please check the website in your browser.
echo.

REM 生成されたファイル一覧を表示
echo Generated files:
echo.
if exist "okuyami_data\*.txt" (
    echo [Fetched Data]
    for %%f in (okuyami_data\*.txt) do echo   - %%f
    echo.
)
if exist "okuyami_output\*.csv" (
    echo [CSV Output]
    for %%f in (okuyami_output\*.csv) do echo   - %%f
    echo.
)
if exist "okuyami_output\*.md" (
    echo [Markdown Output]
    for %%f in (okuyami_output\*.md) do echo   - %%f
    echo.
)

echo Next execution: Run this batch file at the same time tomorrow.
echo Register with Task Scheduler for automatic execution.
echo.

REM 後片付け（元のディレクトリへ戻る）
popd

REM 正常終了（タスク スケジューラーではウィンドウを閉じる）
exit /b 0
