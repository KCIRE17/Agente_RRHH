"""tools.verificar_secretos - escaner anti-secretos del repo."""

from __future__ import annotations

from tools import verificar_secretos as vs


def test_detecta_clave_groq(tmp_path):
    # Se construye en runtime para no incrustar un literal tipo-secreto.
    falso = "gsk_" + "a" * 30
    archivo = tmp_path / "config.txt"
    archivo.write_text(f"GROQ_API_KEY={falso}\n", encoding="utf-8")
    hallazgos = vs._revisar(archivo)
    assert len(hallazgos) == 1
    assert hallazgos[0][1] == "Groq API key"


def test_detecta_token_estilo_github(tmp_path):
    falso = "ghp_" + "B" * 25
    archivo = tmp_path / "cfg.txt"
    archivo.write_text(f"token: {falso}\n", encoding="utf-8")
    assert vs._revisar(archivo)


def test_no_marca_placeholders(tmp_path):
    archivo = tmp_path / "ejemplo.txt"
    archivo.write_text(
        "GROQ_API_KEY=tu_clave_aqui\nGEMINI_API_KEY=<pon-tu-clave>\n", encoding="utf-8"
    )
    assert vs._revisar(archivo) == []


def test_no_marca_archivo_limpio(tmp_path):
    archivo = tmp_path / "limpio.txt"
    archivo.write_text("hola mundo, sin secretos\n", encoding="utf-8")
    assert vs._revisar(archivo) == []


def test_main_falla_con_secreto(tmp_path, capsys):
    falso = "sk-" + "C" * 30
    archivo = tmp_path / "leak.txt"
    archivo.write_text(f"clave={falso}\n", encoding="utf-8")
    assert vs.main([str(archivo)]) == 1


def test_main_ok_sin_secretos(tmp_path):
    archivo = tmp_path / "ok.txt"
    archivo.write_text("nada que ver\n", encoding="utf-8")
    assert vs.main([str(archivo)]) == 0


def test_repo_real_sin_secretos():
    assert vs.main([]) == 0
