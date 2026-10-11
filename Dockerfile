# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Agente RRHH - imagen del MVP en linea (chatbot F4: FastAPI + SPA).
# Usa el mismo entry point que Vercel (api/index.py) sobre data_demo/.
# F3 (Streamlit) NO se conteneriza aqui: segun README 8.4 es de red local.
# Por defecto la IA del chat queda offline (PROVEEDOR_CHAT vacio, costo $0).
# ---------------------------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATA_DIR=data_demo \
    PROVEEDOR_CHAT=

WORKDIR /app

# Dependencias del chatbot (subset de deploy, mismas que Vercel).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Codigo de la aplicacion (api/, src/, config/, prompt/, data_demo/...).
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "api.index:app", "--host", "0.0.0.0", "--port", "8000"]
