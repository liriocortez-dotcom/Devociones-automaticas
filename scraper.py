"""
scraper.py — Extrae devociones desde devocionmatutina.com.
"""

import logging
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://devocionmatutina.com"

CATEGORIAS_OBJETIVO = {
    "adultos",
    "jóvenes",
    "jovenes",
    "damas",
    "adolescentes",
    "menores",
    "niños",
    "ninos",
}

CATEGORIAS_NORMALIZADAS = {
    "jovenes": "Jóvenes",
    "jóvenes": "Jóvenes",
    "ninos": "Niños",
    "niños": "Niños",
    "adultos": "Adultos",
    "damas": "Damas",
    "adolescentes": "Adolescentes",
    "menores": "Menores",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; DevocionesScraper/1.0)"
    )
}

TIMEOUT = 10  # segundos


def _normalizar_categoria(texto: str) -> Optional[str]:
    """Devuelve la categoría normalizada o None si no aplica."""
    clave = texto.strip().lower()
    return CATEGORIAS_NORMALIZADAS.get(clave)


def _get_soup(url: str) -> Optional[BeautifulSoup]:
    """Descarga una URL y devuelve un objeto BeautifulSoup."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as exc:
        logger.error("Error al descargar %s: %s", url, exc)
        return None

def _extraer_imagen(soup: BeautifulSoup) -> str:
    """Extrae la URL de la imagen destacada de un artículo."""
    # Open Graph
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        imagen = og["content"].strip()

        if imagen.startswith("//"):
            imagen = "https:" + imagen

        return imagen

    # Imagen dentro del contenido principal
    figura = soup.find("figure", class_=re.compile(r"wp-block-image|post-thumbnail"))
    if figura:
        img = figura.find("img")
        if img and img.get("src"):
            return img["src"].strip()

    # Cualquier imagen dentro del artículo
    article = soup.find("article") or soup.find("main")
    if article:
        img = article.find("img")
        if img and img.get("src"):
            return img["src"].strip()

    return ""

def _extraer_texto(soup: BeautifulSoup) -> str:
    """Extrae el texto completo del cuerpo del artículo."""
    contenedor = (
        soup.find(class_="entry-content")
        or soup.find(class_="post-content")
        or soup.find(class_="content")
        or soup.find("article")
    )

    if not contenedor:
        return ""

    # Eliminar scripts, estilos, iframes y navegación
    for tag in contenedor.find_all(
        ["script", "style", "iframe", "nav", "footer"]
    ):
        tag.decompose()

    texto = contenedor.get_text("\n", strip=True)

    marcadores = [
        "========================",
        "COMPARTIR",
        "DEJA UN COMENTARIO",
        "Comentarios",
    ]

    for marcador in marcadores:
         if marcador in texto:
             texto = texto.split(marcador)[0]

    return texto.strip()

def _extraer_fecha(soup: BeautifulSoup) -> str:
    """Extrae la fecha de publicación del artículo."""
    time_tag = soup.find("time")
    if time_tag:
        return time_tag.get("datetime", time_tag.get_text(strip=True))
    meta = soup.find("meta", property="article:published_time")
    if meta and meta.get("content"):
        return meta["content"][:10]
    return ""


def _detectar_categoria_desde_url(url: str) -> Optional[str]:
    """Intenta detectar la categoría desde la estructura de la URL."""
    url_lower = url.lower()
    for clave in CATEGORIAS_NORMALIZADAS:
        if clave in url_lower:
            return CATEGORIAS_NORMALIZADAS[clave]
    return None


def _detectar_categoria_desde_soup(soup: BeautifulSoup) -> Optional[str]:
    """Intenta detectar la categoría desde breadcrumbs, tags o título."""
    # Breadcrumbs y categorías de WordPress
    for selector in [
        ".breadcrumb a",
        ".cat-links a",
        ".post-categories a",
        '[rel="category tag"]',
        ".entry-meta a",
    ]:
        elementos = soup.select(selector)
        for el in elementos:
            cat = _normalizar_categoria(el.get_text())
            if cat:
                return cat

    # Título de la página puede contener la categoría
    titulo = soup.title.string if soup.title else ""
    for clave in CATEGORIAS_NORMALIZADAS:
        if clave in titulo.lower():
            return CATEGORIAS_NORMALIZADAS[clave]

    return None


def _scrape_articulo(url: str) -> Optional[dict]:
    """Descarga y parsea un artículo individual."""
    soup = _get_soup(url)
    if not soup:
        return None

    # Título
    h1 = soup.find("h1", class_=re.compile(r"entry-title|post-title|title"))
    if not h1:
        h1 = soup.find("h1")
    titulo = h1.get_text(strip=True) if h1 else ""

    if not titulo:
        logger.warning("Artículo sin título en %s, omitiendo.", url)
        return None

    # Categoría
    categoria = (
        _detectar_categoria_desde_soup(soup)
        or _detectar_categoria_desde_url(url)
    )

    # Último intento: detectar desde el título
    if not categoria:
        titulo_lower = titulo.lower()

        for clave, normalizada in CATEGORIAS_NORMALIZADAS.items():
            if f"para {clave}" in titulo_lower:
                categoria = normalizada
                break

    if not categoria:
        logger.debug(
            "No se pudo determinar categoría para %s, omitiendo.",
            url,
        )
        return None

    fecha = _extraer_fecha(soup)
    imagen = _extraer_imagen(soup)
    texto = _extraer_texto(soup)

    if not texto:
        logger.warning("Artículo sin texto en %s, omitiendo.", url)
        return None

    return {
        "categoria": categoria,
        "titulo": titulo,
        "fecha": fecha,
        "url": url,
        "imagen": imagen,
        "texto": texto,
    }


def _obtener_links_recientes() -> list[str]:
    """
    Obtiene los enlaces a los artículos más recientes desde la página principal.
    Intenta varias estrategias para ser robusto ante cambios de HTML.
    """
    soup = _get_soup(BASE_URL)
    if not soup:
        return []

    links: list[str] = []
    vistos: set[str] = set()

    # Estrategia 1: enlaces dentro de artículos del loop principal
    for article in soup.find_all("article"):
        a = article.find("a", href=True)
        if a:
            href = a["href"].strip()
            if href.startswith("http") and href not in vistos:
                vistos.add(href)
                links.append(href)

    # Estrategia 2: enlaces con clases típicas de títulos de posts
    if not links:
        for a in soup.select("h2.entry-title a"):
            href = a.get("href", "").strip()

            if href.startswith(BASE_URL) and href not in vistos:
                vistos.add(href)
                links.append(href)

    # Estrategia 3: todos los enlaces internos que parezcan artículos
    if not links:
        for a in soup.find_all("a", href=re.compile(rf"^{re.escape(BASE_URL)}/.+")):
            href = a["href"].strip()
            # Excluir páginas de categoría, autor, etc.
            if any(x in href for x in ["/category/", "/tag/", "/author/", "?", "#"]):
                continue
            if href not in vistos:
                vistos.add(href)
                links.append(href)

    logger.info("Links encontrados en página principal: %d", len(links))
    return links


def obtener_devociones() -> list[dict]:
    """
    Punto de entrada principal.
    Devuelve una lista de diccionarios con las seis devociones del día,
    una por cada categoría objetivo.
    """
    links = _obtener_links_recientes()
    if not links:
        logger.error("No se encontraron enlaces en %s", BASE_URL)
        return []

    categorias_encontradas: dict[str, dict] = {}

    for url in links:
        # Si ya tenemos las 6 categorías, no seguir
        if len(categorias_encontradas) == 6:
           break

        articulo = _scrape_articulo(url)
        if not articulo:
            continue

        cat = articulo["categoria"]
        if cat in categorias_encontradas:
            logger.debug("Categoría '%s' ya registrada, omitiendo %s.", cat, url)
            continue

        categorias_encontradas[cat] = articulo
        logger.info("✔ Categoría '%s' extraída desde %s", cat, url)

    resultado = list(categorias_encontradas.values())
    logger.info("Total de devociones extraídas: %d", len(resultado))
    return resultado
