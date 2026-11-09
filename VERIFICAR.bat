@echo off
setlocal
REM ============================================================
REM  VERIFICAR.bat - Diagnostico rapido
REM  Compila, escanea secretos y simula F1 y F2 sin gastar
REM  cuota ni tocar datos. Ideal al llegar a otra PC.
REM  Usa .venv si existe; si no, uv run python.
REM ============================================================
cd /d "%~dp0"
call "%~dp0_entorno.bat"
if errorlevel 1 (
    echo.
    pause
    exit /b 1
)
echo  --- 1/4 Compilacion -------------------------------
%RUN_CMD% -m compileall -q src main.py
if errorlevel 1 ( echo  [ERROR] Compilacion con errores. & goto :fin )
echo  Ok.
echo.
echo  --- 2/4 Escaneo anti-secretos ----------------------
%RUN_CMD% tools/verificar_secretos.py
echo.
echo  --- 3/4 F1 --dry-run (sin cuota, sin guardar) ------
%RUN_CMD% main.py --dry-run
echo.
echo  --- 4/4 F2 --dry-run (sin cuota, sin guardar) ------
%RUN_CMD% main.py evaluar --dry-run
echo.
echo  Diagnostico completo. Si algo fallo aqui, revisa el .env.
:fin
echo.
pause
