@echo off
setlocal
REM ============================================================
REM  EVALUAR.bat - Fase 2: Match Score (Groq)
REM  Evalua los candidatos "Listos" de silver y escribe gold.
REM  Usa .venv si existe; si no, uv run python.
REM ============================================================
cd /d "%~dp0"
call "%~dp0_entorno.bat"
if errorlevel 1 (
    echo.
    pause
    exit /b 1
)
echo  [F2] Evaluando candidatos (silver -^> gold, Match Score)...
%RUN_CMD% main.py evaluar
echo.
echo  Listo. Revisa data\gold\evaluacion\ para el ranking.
pause
