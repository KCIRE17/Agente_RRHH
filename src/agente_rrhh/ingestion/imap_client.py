"""Conexión IMAP a Gmail, filtrado de asunto y descarga de adjuntos."""

from __future__ import annotations

import hashlib
import imaplib
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from email import policy
from email.header import decode_header, make_header
from email.message import Message
from email.parser import BytesParser
from email.utils import parseaddr, parsedate_to_datetime

from ..core.config import IMAP_HOST, IMAP_PUERTO, PREFIJO_ASUNTO, Config


def _primera_palabra_ascii(prefijo: str) -> str | None:
    """Primera palabra del prefijo si es ASCII (para la búsqueda IMAP)."""
    if not prefijo:
        return None
    palabra = prefijo.split()[0]
    return palabra if palabra.isascii() else None


@dataclass
class Postulacion:
    numero: bytes
    mensaje_id: str
    asunto: str
    vacante_id: str
    remitente: str
    adjuntos: list[tuple[str, bytes]] = field(default_factory=list)
    cuerpo: str = ""
    remitente_nombre: str = ""
    remitente_email: str = ""
    remitente_dominio: str = ""
    fecha_envio: datetime | None = None
    x_mailer: str = ""


def _dominio_de(correo: str) -> str:
    return correo.rsplit("@", 1)[-1] if "@" in correo else ""


def _fecha_del_cabecera(mensaje: Message) -> datetime | None:
    cabeza = mensaje.get("Date")
    if not cabeza:
        return None
    try:
        return parsedate_to_datetime(cabeza)
    except (TypeError, ValueError, OverflowError):
        return None


def _decodificar_cabecera(valor: str | None) -> str:
    if not valor:
        return ""
    try:
        return str(make_header(decode_header(valor)))
    except Exception:
        return str(valor)


def _extraer_adjuntos(mensaje: Message) -> list[tuple[str, bytes]]:
    adjuntos: list[tuple[str, bytes]] = []
    if mensaje.is_multipart():
        for parte in mensaje.walk():
            nombre = parte.get_filename()
            if not nombre:
                continue
            contenido = parte.get_payload(decode=True)
            adjuntos.append((_decodificar_cabecera(nombre), contenido or b""))
    else:
        nombre = mensaje.get_filename()
        if nombre:
            adjuntos.append((_decodificar_cabecera(nombre), mensaje.get_payload(decode=True) or b""))
    return adjuntos


def _extraer_cuerpo(mensaje: Message) -> str:
    def _decodificar(parte: Message) -> str:
        payload = parte.get_payload(decode=True)
        if payload is None:
            return ""
        codificacion = parte.get_content_charset() or "utf-8"
        return payload.decode(codificacion, errors="replace")

    if mensaje.is_multipart():
        partes = []
        for parte in mensaje.walk():
            if parte.get_content_type() == "text/plain":
                partes.append(_decodificar(parte))
        return "\n".join(partes)

    if mensaje.get_content_type() == "text/plain":
        return _decodificar(mensaje)
    return ""


class ImapClient:
    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._mail: imaplib.IMAP4_SSL | None = None

    def conectar(self) -> "ImapClient":
        self._mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PUERTO, timeout=self._cfg.imap_timeout)
        self._mail.login(self._cfg.email, self._cfg.password)
        self._mail.select("INBOX")
        return self

    def cerrar(self) -> None:
        if self._mail:
            try:
                self._mail.close()
            finally:
                self._mail.logout()

    def _buscar_no_leidos(self) -> list[bytes]:
        """UNSEEN, opcionalmente SINCE <fecha> y SUBJECT <primera palabra del asunto>.

        Todo el filtrado pesado ocurre en el servidor para no escanear el
        historial completo de la bandeja.
        """
        assert self._mail is not None

        fecha = None
        if self._cfg.dias_atras > 0:
            fecha = (date.today() - timedelta(days=self._cfg.dias_atras - 1)).strftime(
                "%d-%b-%Y"
            )

        token = _primera_palabra_ascii(self._cfg.asunto)
        base = ["UNSEEN"]
        if fecha:
            base.append(f'SINCE "{fecha}"')

        intentos = []
        if token:
            intentos.append(base + [f'SUBJECT "{token}"'])
        intentos.append(base)

        for criterios in intentos:
            try:
                estado, datos = self._mail.search(None, *criterios)
            except imaplib.IMAP4.error:
                continue
            if estado == "OK":
                return datos[0].split() if datos and datos[0] else []
        return []

    def _leer_mensaje(self, numero: bytes) -> Message | None:
        assert self._mail is not None
        estado, datos = self._mail.fetch(numero, "(BODY.PEEK[])")
        if estado != "OK" or not datos:
            return None
        crudo = datos[0][1]
        return BytesParser(policy=policy.default).parsebytes(crudo)

    def listar_postulaciones(self) -> list[Postulacion]:
        """Devuelve los correos no leídos cuyo asunto inicia con el prefijo configurado."""
        prefijo = (self._cfg.asunto or PREFIJO_ASUNTO).strip() or PREFIJO_ASUNTO
        postulaciones: list[Postulacion] = []
        for numero in self._buscar_no_leidos():
            mensaje = self._leer_mensaje(numero)
            if mensaje is None:
                continue

            asunto = _decodificar_cabecera(mensaje.get("Subject"))
            if not asunto.startswith(prefijo):
                continue

            vacante = asunto[len(prefijo):].strip()

            remitente_decodificado = _decodificar_cabecera(mensaje.get("From"))
            remitente_nombre, remitente_email = parseaddr(remitente_decodificado)
            fecha_envio = _fecha_del_cabecera(mensaje)

            mensaje_id = mensaje.get("Message-ID", "").strip()
            if not mensaje_id:
                base = "|".join(
                    [
                        remitente_email,
                        fecha_envio.isoformat() if fecha_envio else "",
                        vacante,
                        asunto,
                    ]
                )
                mensaje_id = f"sin-id|{hashlib.sha1(base.encode('utf-8')).hexdigest()}"

            postulaciones.append(
                Postulacion(
                    numero=numero,
                    mensaje_id=mensaje_id,
                    asunto=asunto,
                    vacante_id=vacante,
                    remitente=remitente_decodificado,
                    adjuntos=_extraer_adjuntos(mensaje),
                    cuerpo=_extraer_cuerpo(mensaje),
                    remitente_nombre=remitente_nombre.strip(),
                    remitente_email=remitente_email,
                    remitente_dominio=_dominio_de(remitente_email),
                    fecha_envio=fecha_envio,
                    x_mailer=(mensaje.get("X-Mailer") or "").strip(),
                )
            )
        return postulaciones

    def marcar_leido(self, numero: bytes) -> None:
        assert self._mail is not None
        try:
            self._mail.store(numero, "+FLAGS", r"(\Seen)")
        except Exception:
            pass