@echo off
setlocal
chcp 65001 >nul

rem Locate the EStudy env Python (try common install locations)
set "PY=%USERPROFILE%\.conda\envs\EStudy\python.exe"
if not exist "%PY%" set "PY=D:\ProgramData\miniconda3\envs\EStudy\python.exe"
if not exist "%PY%" set "PY=C:\ProgramData\miniconda3\envs\EStudy\python.exe"

if not exist "%PY%" (
    echo [ERROR] EStudy Python not found:
    echo         %PY%
    echo Please edit this file and set PY to your EStudy python.exe path.
    pause
    exit /b 1
)

echo [1/2] Starting backend on port 8080 ...
start "EStudy Backend" /D "%~dp0backend" cmd /k ""%PY%" -m uvicorn main:app --reload --port 8080"

echo [2/2] Starting frontend on port 5175 ...
start "EStudy Frontend" /D "%~dp0frontend" cmd /k "npm.cmd run dev"

echo Waiting for services to start...
%SystemRoot%\System32\timeout.exe /t 8 /nobreak >nul

echo Opening http://localhost:5175 ...
start "" http://localhost:5175

echo.
echo ==============================
echo  Backend : http://localhost:8080
echo  Frontend: http://localhost:5175
echo  Stop    : close the two console windows
echo ==============================
pause
