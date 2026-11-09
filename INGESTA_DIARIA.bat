@echo off
setlocal
REM ============================================================
REM  INGESTA_DIARIA.bat - F1 programado
REM  Agenda el lote diario a la hora HORA_INGESTA del .env
REM  (default 18:00) y lo deja corriendo. Ctrl+C para salir.
REM  Usa .venv si existe; si no, uv run python.
REM ============================================================
cd /d "%~dp0"
call "%~dp0_entorno.bat"
if errorlevel 1 (
    echo.
    pause
    exit /b 1
)
echo  [F1] Programando lote diario (hora del .env). Ctrl+C para salir.
%RUN_CMD% main.py --programar
pause
