"""
telegram_bot.py — Envía resúmenes de devociones a Telegram para revisión humana.
"""

import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
PREVIEW_CHARS = 500
RETRY_DELAY = 3  # segundos entre reintentos
MAX_RETRIES = 3


def _get_credentials() -> tuple[str, str]:
    """Lee las credenciales desde variables de entorno."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token:
        raise EnvironmentError("Variable de entorno TELEGRAM_BOT_TOKEN no definida.")
    if not chat_id:
        raise EnvironmentError("Variable de entorno TELEGRAM_CHAT_ID no definida.")
    return token, chat_id


def _formatear_mensaje(devocion: dict) -> str:
    """Construye el texto del mensaje de Telegram para una devoción."""
    categoria = devocion.get("categoria", "Desconocida").upper()
    fecha = devocion.get("fecha", "Sin fecha")
    titulo = devocion.get("titulo", "Sin título")
    texto = devocion.get("texto", "")
    url = devocion.get("url", "")

    preview = texto[:PREVIEW_CHARS]
    if len(texto) > PREVIEW_CHARS:
        preview += "…"

    mensaje = (
        f"📖 {categoria}\n\n"
        f"Fecha:\n{fecha}\n\n"
        f"Título:\n{titulo}\n\n"
        f"Vista previa:\n{preview}\n\n"
        f"Enlace:\n{url}\n\n"
        f"Estado:\nLISTO PARA PUBLICAR"
    )
    return mensaje


def _enviar_mensaje(token: str, chat_id: str, texto: str) -> bool:
    """
    Envía un único mensaje de texto a Telegram.
    Reintenta hasta MAX_RETRIES veces ante errores de red.
    Devuelve True si el envío fue exitoso.
    """
    url = TELEGRAM_API.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": texto,
        "disable_web_page_preview": True,
    }

    for intento in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(url, json=payload, timeout=15)
            data = resp.json()
            if data.get("ok"):
                return True
            logger.warning(
                "Telegram rechazó el mensaje (intento %d/%d): %s",
                intento, MAX_RETRIES, data.get("description", "Sin descripción"),
            )
        except requests.RequestException as exc:
            logger.warning("Error de red Telegram (intento %d/%d): %s", intento, MAX_RETRIES, exc)

        if intento < MAX_RETRIES:
            time.sleep(RETRY_DELAY)

    return False


def enviar_resumen(devociones: list[dict]) -> None:
    """
    Envía un mensaje de Telegram por cada devoción recibida.
    Espera 1 segundo entre mensajes para respetar los límites de la API.
    """
    token, chat_id = _get_credentials()

    if not devociones:
        logger.warning("No hay devociones para enviar a Telegram.")
        return

    total = len(devociones)
    enviados = 0

    for i, devocion in enumerate(devociones, start=1):
        categoria = devocion.get("categoria", "Desconocida")
        logger.info("Enviando mensaje %d/%d a Telegram [%s]…", i, total, categoria)

        mensaje = _formatear_mensaje(devocion)
        exito = _enviar_mensaje(token, chat_id, mensaje)

        if exito:
            enviados += 1
            logger.info("✔ Mensaje enviado: [%s]", categoria)
        else:
            logger.error("✘ No se pudo enviar el mensaje para [%s]", categoria)

        # Pausa entre mensajes para no saturar la API de Telegram
        if i < total:
            time.sleep(1)

    logger.info("Telegram: %d/%d mensajes enviados exitosamente.", enviados, total)
