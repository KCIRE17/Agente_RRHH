"""F4 - API web del chatbot (FastAPI + TestClient)."""

from __future__ import annotations


def test_health_offline(client_demo):
    r = client_demo.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["modo"] == "offline"
    assert body["data_dir"] == "data_demo"
    assert body["login"] == "desactivado"


def test_vacantes(client_demo):
    r = client_demo.get("/api/vacantes")
    assert r.status_code == 200
    vacantes = r.json()["vacantes"]
    assert len(vacantes) == 3
    assert all(v["total"] == 10 for v in vacantes)


def test_ranking_por_defecto(client_demo):
    r = client_demo.get("/api/ranking")
    assert r.status_code == 200
    body = r.json()
    assert body["carpeta"] == "ANALISTA_DE_DATOS"
    assert len(body["candidatos"]) == 10


def test_ranking_carpeta_inexistente(client_demo):
    r = client_demo.get("/api/ranking", params={"carpeta": "NO_EXISTE"})
    assert r.status_code == 404


def test_brechas(client_demo):
    r = client_demo.get("/api/brechas")
    assert r.status_code == 200
    body = r.json()
    assert body["total_candidatos"] == 30
    assert isinstance(body["brechas"], list)


def test_costos_offline(client_demo):
    r = client_demo.get("/api/costos")
    assert r.status_code == 200
    body = r.json()
    assert body["offline"] is True
    assert body["fase2"]["candidatos"] == 30
    assert body["chat"]["llamadas"] == 0
    assert body["costo_total_usd"] == 0.0


def test_simular_pesos_por_defecto(client_demo):
    r = client_demo.post("/api/simular", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["pesos"] == {"habilidades": 0.5, "experiencia": 0.3, "formacion": 0.2}
    assert len(body["resultados"]) == 30


def test_simular_filtrado_por_vacante(client_demo):
    r = client_demo.post("/api/simular", json={"vacante": "ANALISTA_DE_DATOS"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["resultados"]) == 10
    assert all(x["vacante"] == "ANALISTA_DE_DATOS" for x in body["resultados"])


def test_faq(client_demo):
    r = client_demo.get("/api/faq")
    assert r.status_code == 200
    assert len(r.json()["preguntas"]) == 8


def test_config_publica(client_demo):
    r = client_demo.get("/api/config")
    assert r.status_code == 200
    body = r.json()
    assert body["offline"] is True
    assert isinstance(body["tarifas"], dict)


def test_chat_ranking_offline(client_demo):
    r = client_demo.post("/api/chat", json={"mensaje": "ranking de ANALISTA DE DATOS"})
    assert r.status_code == 200
    body = r.json()
    assert body["intencion"] == "ranking"
    assert body["modo"] == "offline"
    assert body["sesion_id"]


def test_chat_fallback_trae_faq(client_demo):
    r = client_demo.post("/api/chat", json={"mensaje": "qwerty zxcvb"})
    assert r.status_code == 200
    body = r.json()
    assert body["intencion"] == "fallback"
    assert "aviso" in body


def test_chat_valida_mensaje_vacio(client_demo):
    r = client_demo.post("/api/chat", json={"mensaje": ""})
    assert r.status_code == 422


def test_sesion_nueva(client_demo):
    r = client_demo.post("/api/sesiones/nueva")
    assert r.status_code == 200
    assert r.json()["sesion_id"]


def test_spa_y_estaticos(client_demo):
    assert client_demo.get("/").status_code == 200
    assert client_demo.get("/static/app.js").status_code == 200
    assert client_demo.get("/static/style.css").status_code == 200


# --------------------------------------------------------------------- login
def test_login_desactivado_devuelve_503(client_demo):
    r = client_demo.post("/api/login", json={"usuario": "x", "clave": "y"})
    assert r.status_code == 503


def test_me_sin_login(client_demo):
    body = client_demo.get("/api/me").json()
    assert body == {"autenticado": False, "login_habilitado": False}


def test_endpoint_protegido_sin_token(client_login):
    r = client_login.get("/api/vacantes")
    assert r.status_code == 401


def test_login_credenciales_invalidas(client_login):
    r = client_login.post("/api/login", json={"usuario": "rrhh", "clave": "mala"})
    assert r.status_code == 401


def test_flujo_login_logout(client_login):
    r = client_login.post(
        "/api/login", json={"usuario": "rrhh", "clave": "clave-demo-123"}
    )
    assert r.status_code == 200
    token = r.json()["token"]
    cabecera = {"Authorization": f"Bearer {token}"}

    assert client_login.get("/api/vacantes", headers=cabecera).status_code == 200
    assert (
        client_login.post("/api/chat", json={"mensaje": "hola"}, headers=cabecera).status_code
        == 200
    )
    assert client_login.get("/api/me", headers=cabecera).json()["autenticado"] is True

    assert client_login.post("/api/logout", headers=cabecera).status_code == 200
    assert client_login.get("/api/me", headers=cabecera).json()["autenticado"] is False
