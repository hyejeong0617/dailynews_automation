@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul || (echo Python is required.& pause & exit /b 1)
where git >nul 2>nul || (echo Git is required.& pause & exit /b 1)
if not exist .env (echo Copy .env.example to .env and set NOTION_TOKEN.& pause & exit /b 1)
if not exist .venv\Scripts\python.exe (
  python -m venv .venv
  if errorlevel 1 goto :fail
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  if errorlevel 1 goto :fail
)
git pull --ff-only
if errorlevel 1 goto :fail
.venv\Scripts\python.exe request_news_local.py
if errorlevel 1 goto :fail
echo Done. GitHub Actions will generate the requested summaries.
pause
exit /b 0
:fail
echo The request did not finish. Read the error above.
pause
exit /b 1
