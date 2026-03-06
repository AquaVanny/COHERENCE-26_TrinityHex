@echo off
echo ========================================
echo Clinical Trial Matching Platform
echo Starting Demo Environment...
echo ========================================
echo.

echo [1/2] Starting Flask Backend...
start "Flask Backend" cmd /k "cd python-api && python app.py"
timeout /t 5 /nobreak >nul

echo [2/2] Starting React Frontend...
start "React Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo Demo servers starting!
echo.
echo Backend: http://localhost:5000
echo Frontend: http://localhost:5173
echo.
echo Press any key to open browser...
echo ========================================
pause >nul

start http://localhost:5173

echo.
echo Demo environment ready!
echo Close this window when done.
pause
