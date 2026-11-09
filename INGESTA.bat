@echo off
setlocal
REM ============================================================
REM  INGESTA.bat - Fase 1: lote real (IMAP + Gemini + silver)
REM  Doble clic y funciona: procesa los correos de hoy.
REM  Usa .venv si existe; si no, uv run python.
REM ============================================================
cd /d "%~dp0"
call "%~dp0_entorno.bat"
if errorlevel 1 (
    echo.
    pause
    exit /b 1
)
echo  [F1] Procesando postulaciones (IMAP + extraccion IA)...
%RUN_CMD% main.py
echo.
echo  Listo. Revisa logs\ingesta.log para el resumen.
pause
