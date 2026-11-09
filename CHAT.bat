@echo off
setlocal
REM ============================================================
REM  CHAT.bat - Fase 4: chatbot web (F4)
REM  Abre el navegador y lanza el chatbot en localhost:8510.
REM  Ctrl+C para salir.
REM  Usa .venv si existe; si no, uv run python.
REM ============================================================
cd /d "%~dp0"
call "%~dp0_entorno.bat"
if errorlevel 1 (
    echo.
    pause
    exit /b 1
)
start "" http://127.0.0.1:8510
%RUN_CMD% main.py chat --port 8510
pause
