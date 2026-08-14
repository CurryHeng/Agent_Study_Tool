@echo off
setlocal

rem Locate the EStudy env Python via %USERPROFILE% (no hardcoded non-ASCII path)
set "PY=%USERPROFILE%\.conda\envs\EStudy\python.exe"

if not exist "%PY%" (
    echo [ERROR] EStudy Python not found:
    echo         %PY%
    echo Please edit this file and set PY to your EStudy python.exe path.
    pause
    exit /b 1
)

echo [1/2] Starting backend on port 8080 ...
start "EStudy Backend" /D "%~dp0backend" cmd /k "%PY% -m uvicorn main:app --reload --port 8080"

echo [2/2] Starting frontend on port 5173 ...
start "EStudy Frontend" /D "%~dp0frontend" cmd /k "npm run dev"

echo Waiting for services to start...
timeout /t 8 /nobreak >nul

echo Opening http://localhost:5175 ...
start "" http://localhost:5175

echo.
echo ==============================
echo  Backend : http://localhost:8080
echo  Frontend: http://localhost:5175
echo  Stop    : close the two console windows
echo ==============================
pause
