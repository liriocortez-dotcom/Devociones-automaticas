"""
main.py — Punto de entrada del sistema de devociones automatizadas.

Modos de uso:
    python main.py revisar   → Extrae devociones y las envía a Telegram para revisión.
    python main.py publicar  → Extrae devociones y las publica en Facebook.
"""

import logging
import sys

import scraper
import telegram_bot
import facebook

# ──────────────────────────────────────────────
# Configuración de logging
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Modos
# ──────────────────────────────────────────────

def modo_revisar() -> None:
    """
    Extrae las devociones del día y las envía a Telegram
    para revisión humana. No publica en Facebook.
    """
    logger.info("═══ MODO: REVISAR ═══")

    logger.info("Extrayendo devociones…")
    devociones = scraper.obtener_devociones()

    if not devociones:
        logger.error("No se pudo extraer ninguna devoción. Abortando.")
        sys.exit(1)

    logger.info("%d devoción(es) encontradas.", len(devociones))

    telegram_bot.enviar_resumen(devociones)

    logger.info("═══ REVISIÓN COMPLETADA ═══")


def modo_publicar() -> None:
    """
    Extrae las devociones del día y las publica en Facebook.
    """
    logger.info("═══ MODO: PUBLICAR ═══")

    logger.info("Extrayendo devociones…")
    devociones = scraper.obtener_devociones()

    if not devociones:
        logger.error("No se pudo extraer ninguna devoción. Abortando.")
        sys.exit(1)

    logger.info("%d devoción(es) encontradas.", len(devociones))

    publicadas = facebook.publicar_devociones(devociones)

    logger.info(
        "═══ PUBLICACIÓN COMPLETADA: %d/%d ═══",
        len(publicadas),
        len(devociones),
    )

    if len(publicadas) < len(devociones):
        fallidas = len(devociones) - len(publicadas)

        logger.error(
            "%d devoción(es) no se pudieron publicar.",
            fallidas,
        )

        sys.exit(1)


# ──────────────────────────────────────────────
# Punto de entrada
# ──────────────────────────────────────────────

MODOS = {
    "revisar": modo_revisar,
    "publicar": modo_publicar,
}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in MODOS:
        print(f"Uso: python main.py [{'|'.join(MODOS)}]")
        sys.exit(1)

    MODOS[sys.argv[1]]()
    