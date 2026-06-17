"""
facebook.py — Publica devociones en una página de Facebook mediante Graph API.
"""

import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

GRAPH_API = "https://graph.facebook.com/v19.0"
RETRY_DELAY = 5  # segundos entre reintentos
MAX_RETRIES = 3


def _get_credentials() -> tuple[str, str]:
    """Lee las credenciales desde variables de entorno."""
    token = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()
    page_id = os.environ.get("FACEBOOK_PAGE_ID", "").strip()
    if not token:
        raise EnvironmentError("Variable de entorno FACEBOOK_PAGE_ACCESS_TOKEN no definida.")
    if not page_id:
        raise EnvironmentError("Variable de entorno FACEBOOK_PAGE_ID no definida.")
    return token, page_id


def _formatear_publicacion(devocion: dict) -> str:
    """Construye el cuerpo del post de Facebook."""
    categoria = devocion.get("categoria", "Desconocida").upper()
    texto = devocion.get("texto", "")
    url = devocion.get("url", "")

    publicacion = (
        f"📖 DEVOCIÓN MATUTINA PARA {categoria}\n\n"
        f"{texto}\n\n"
        f"Fuente:\n{url}"
    )
    return publicacion


def _publicar_post(
    token: str,
    page_id: str,
    mensaje: str,
    imagen_url: str,
) -> bool:
    """
    Publica un post en Facebook.
    Si hay imagen, usa el endpoint /photos para adjuntarla.
    Si no hay imagen, usa el endpoint /feed.
    Devuelve True si la publicación fue exitosa.
    """
    for intento in range(1, MAX_RETRIES + 1):
        try:
            if imagen_url:
                endpoint = f"{GRAPH_API}/{page_id}/photos"
                payload = {
                    "access_token": token,
                    "caption": mensaje,
                    "url": imagen_url,
                }
            else:
                endpoint = f"{GRAPH_API}/{page_id}/feed"
                payload = {
                    "access_token": token,
                    "message": mensaje,
                }

            resp = requests.post(endpoint, data=payload, timeout=30)
            data = resp.json()

            if resp.ok and ("id" in data or "post_id" in data):
                post_id = data.get("id") or data.get("post_id")
                logger.info("✔ Publicado en Facebook con ID: %s", post_id)
                return True

            error = data.get("error", {})
            logger.warning(
                "Facebook rechazó la publicación (intento %d/%d): [%s] %s",
                intento, MAX_RETRIES,
                error.get("code", "?"),
                error.get("message", str(data)),
            )

        except requests.RequestException as exc:
            logger.warning(
                "Error de red Facebook (intento %d/%d): %s", intento, MAX_RETRIES, exc
            )

        if intento < MAX_RETRIES:
            time.sleep(RETRY_DELAY)

    return False


def publicar_devociones(devociones: list[dict]) -> list[dict]:
    """
    Publica cada devoción en Facebook.
    Devuelve la lista de devociones publicadas exitosamente.
    """
    token, page_id = _get_credentials()

    if not devociones:
        logger.warning("No hay devociones para publicar en Facebook.")
        return []

    publicadas: list[dict] = []
    total = len(devociones)

    for i, devocion in enumerate(devociones, start=1):
        categoria = devocion.get("categoria", "Desconocida")
        logger.info("Publicando %d/%d en Facebook [%s]…", i, total, categoria)

        mensaje = _formatear_publicacion(devocion)
        imagen = devocion.get("imagen", "")

        exito = _publicar_post(token, page_id, mensaje, imagen)

        if exito:
            publicadas.append(devocion)
        else:
            logger.error("✘ No se pudo publicar [%s]", categoria)

        # Pausa entre publicaciones para respetar límites de la API
        if i < total:
            time.sleep(2)

    logger.info(
        "Facebook: %d/%d devociones publicadas exitosamente.", len(publicadas), total
    )
    return publicadas
