@echo off
setlocal EnableExtensions
REM ============================================================
REM  INSTALAR.bat - Setup de una sola vez en la PC nueva
REM  Orden de instalacion:
REM    1) uv si ya existe            -> uv sync
REM    2) instalar uv (PowerShell)   -> uv sync
REM    3) instalar uv via pip        -> uv sync
REM    4) si uv es imposible         -> .venv + pip (requirements-full.txt)
REM  No toca .env si ya existe.
REM ============================================================
cd /d "%~dp0"

echo.
echo  ==========================================
echo   Instalando Agente RRHH en esta PC...
echo  ==========================================
echo.

REM ---- 1) Python presente? --------------------------------
where python >NUL 2>&1
if errorlevel 1 (
    echo  [ERROR] No se encontro Python.
    echo  1^) Descarga Python 3.12: https://www.python.org/downloads/
    echo  2^) Al instalarlo marca "Add Python to PATH".
    echo  3^) Vuelve a ejecutar este archivo.
    echo.
    goto :fin_error
)
for /f "delims=" %%V in ('python --version 2^>^&1') do echo   Python detectado: %%V
for /f "tokens=2 delims=." %%M in ('python -c "import sys;print(sys.version.split()[0])"') do (
    if %%M LSS 12 echo   [AVISO] Se recomienda Python 3.12 o superior.
)
echo.

REM ---- 2) uv disponible? ----------------------------------
set "UV_CMD="
where uv >NUL 2>&1
if not errorlevel 1 (
    set "UV_CMD=uv"
    goto :tiene_uv
)
python -m uv --version >NUL 2>&1
if not errorlevel 1 (
    set "UV_CMD=python -m uv"
    goto :tiene_uv
)

echo   uv no encontrado. Instalando (recomendado)...
powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex" >NUL 2>&1
if exist "%USERPROFILE%\.local\bin\uv.exe" set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >NUL 2>&1
if not errorlevel 1 (
    set "UV_CMD=uv"
    goto :tiene_uv
)

echo   Instalador oficial no disponible; probando pip...
python -m pip install --user --upgrade uv >NUL 2>&1
python -m uv --version >NUL 2>&1
if not errorlevel 1 (
    set "UV_CMD=python -m uv"
    goto :tiene_uv
)

echo   [AVISO] No se pudo instalar uv. Usando fallback con pip.
goto :fallback_pip

:tiene_uv
echo   uv disponible (%UV_CMD%). Sincronizando dependencias (uv sync)...
call %UV_CMD% sync
if errorlevel 1 (
    echo  [ERROR] Fallo uv sync. Revisa la salida de arriba.
    echo  Si persiste, borra .venv y vuelve a ejecutar INSTALAR.bat.
    echo.
    goto :fin_error
)
if not exist ".venv\Scripts\python.exe" (
    echo  [ERROR] uv sync no genero .venv\Scripts\python.exe.
    goto :fin_error
)
set "RUN_CMD=.venv\Scripts\python.exe"
goto :post_env

:fallback_pip
echo.
echo   ==========================================
echo    MODO FALLBACK pip (uv no disponible)
echo   ==========================================
if not exist ".venv\Scripts\python.exe" (
    echo   Creando entorno virtual .venv...
    python -m venv .venv
    if errorlevel 1 (
        echo  [ERROR] No se pudo crear .venv.
        goto :fin_error
    )
)
echo   Instalando dependencias completas (requirements-full.txt)...
".venv\Scripts\python.exe" -m pip install --upgrade pip >NUL 2>&1
".venv\Scripts\python.exe" -m pip install -r requirements-full.txt
if errorlevel 1 (
    echo  [ERROR] Fallo pip install. Revisa la salida de arriba.
    echo.
    goto :fin_error
)
set "RUN_CMD=.venv\Scripts\python.exe"
goto :post_env

:post_env
echo.
REM ---- 3) .env: solo si NO existe --------------------------
if not exist ".env" (
    if exist ".env.example" (
        echo   Creando .env desde .env.example ^(completa las claves luego^)...
        copy /Y ".env.example" ".env" >NUL
    )
) else (
    echo   .env ya existe. OK.
)

REM ---- 4) Hook anti-secretos (una vez) ---------------------
git config core.hooksPath .githooks 2>NUL
if errorlevel 1 (
    echo   [AVISO] No se pudo activar el hook ^(git no disponible o no es repo^).
) else (
    echo   Hook anti-secretos activado.
)

REM ---- 5) Verificacion rapida ------------------------------
echo.
echo   Verificando compilacion y secretos...
%RUN_CMD% -m compileall -q src main.py
if errorlevel 1 (
    echo  [AVISO] Compilacion con errores.
    goto :fin
)
%RUN_CMD% tools/verificar_secretos.py
echo.
echo  ==========================================
echo   Listo.
echo   - INGESTA.bat        F1: procesa el correo
echo   - EVALUAR.bat        F2: puntua candidatos
echo   - DASHBOARD.bat      F3: panel Streamlit
echo   - CHAT.bat           F4: chatbot web
echo   Ahora abre INGESTA.bat para probarlo.
echo  ==========================================
goto :fin

:fin_error
echo.
echo  Instalacion no completada. Revisa los mensajes de arriba.
:fin
echo.
pause
exit /b
