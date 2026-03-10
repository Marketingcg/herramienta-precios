"""
FASE 5 — Scraper de tiendas competidoras
Se usa como fallback cuando HardGamers no encuentra resultados.
"""

import asyncio
import re
from playwright.async_api import async_playwright
from hardgamers_scraper import construir_query, es_relevante, detectar_categoria

# ─── Configuración de tiendas ───────────────────────────────────────────────

TIENDAS = [
    {
        "nombre": "CompraGamer",
        "url": "https://compragamer.com/productos?criterio={query}",
        "tipo": "compragamer",
    },
]


# ─── Parsers por tienda ──────────────────────────────────────────────────────

async def parsear_compragamer(page) -> list:
    """CompraGamer — tarjetas de producto individuales (excluye combos y PCs armadas)"""
    resultados = []
    try:
        await page.wait_for_selector(".sc-bcXHqe, .product-card, [class*='ProductCard'], [class*='product']", timeout=10000)
    except Exception:
        pass
    await page.wait_for_timeout(2000)

    # Obtener todas las tarjetas
    items = []
    for sel in ["[class*='ProductCard']", "[class*='product-card']", "[class*='ProductItem']", "article", "[class*='Card']"]:
        items = await page.query_selector_all(sel)
        if len(items) > 2:
            break

    for item in items[:40]:
        try:
            # Excluir combos y PCs armadas
            texto_item = (await item.inner_text()).upper()
            if any(x in texto_item for x in ["COMBO", "PC ARMADA", "PC GAMER", "KIT MOTHER"]):
                continue

            nombre = ""
            for sel in ["p", "h2", "h3", "[class*='name']", "[class*='title']", "[class*='Name']"]:
                els = await item.query_selector_all(sel)
                for el in els:
                    txt = (await el.inner_text()).strip()
                    if len(txt) > 10 and "$" not in txt:
                        nombre = txt
                        break
                if nombre:
                    break

            precio = None
            for sel in ["[class*='price']", "[class*='Price']", "[class*='precio']", "strong", "b"]:
                el = await item.query_selector(sel)
                if el:
                    txt = (await el.inner_text()).strip()
                    p = limpiar_precio(txt)
                    if p and p > 1000:
                        precio = p
                        break

            if nombre and precio:
                resultados.append({
                    "nombre": nombre, "precio": precio,
                    "tienda": "CompraGamer", "stock": "En stock", "url": ""
                })
        except Exception:
            pass

    return resultados


async def parsear_mexx(page) -> list:
    """Mexx — grilla de productos"""
    resultados = []
    try:
        await page.wait_for_selector(".products-list, .product-item, .col-product", timeout=10000)
    except Exception:
        pass
    await page.wait_for_timeout(1500)

    items = await page.query_selector_all(".product-item")
    if not items:
        items = await page.query_selector_all(".col-product")
    if not items:
        items = await page.query_selector_all("[class*='product']")

    for item in items[:30]:
        try:
            nombre = ""
            for sel in [".product-name", ".nombre", "h2", "h3", "a[title]"]:
                el = await item.query_selector(sel)
                if el:
                    nombre = (await el.inner_text()).strip() or await el.get_attribute("title") or ""
                    if nombre:
                        break

            precio = None
            for sel in [".product-price", ".precio", ".price", "[class*='price']", "[class*='precio']"]:
                el = await item.query_selector(sel)
                if el:
                    txt = (await el.inner_text()).strip()
                    precio = limpiar_precio(txt)
                    if precio:
                        break

            if nombre and precio:
                resultados.append({"nombre": nombre, "precio": precio, "tienda": "Mexx", "stock": "En stock", "url": ""})
        except Exception:
            pass

    return resultados


async def parsear_generico(page, nombre_tienda: str) -> list:
    """Parser genérico para tiendas con estructura similar"""
    resultados = []
    try:
        await page.wait_for_selector("body", timeout=10000)
    except Exception:
        pass
    await page.wait_for_timeout(2000)

    # Intentar extraer precios y nombres del DOM
    items = []
    for sel in [
        "article", ".product", ".product-item", ".item",
        "[class*='product']", ".card", "[class*='card']"
    ]:
        items = await page.query_selector_all(sel)
        if len(items) > 2:
            break

    for item in items[:30]:
        try:
            nombre = ""
            for sel in ["h1", "h2", "h3", ".name", ".title", "[class*='name']", "[class*='title']", "a"]:
                el = await item.query_selector(sel)
                if el:
                    txt = (await el.inner_text()).strip()
                    if len(txt) > 5:
                        nombre = txt
                        break

            precio = None
            for sel in [".price", ".precio", "[class*='price']", "[class*='precio']", "strong", "b"]:
                el = await item.query_selector(sel)
                if el:
                    txt = (await el.inner_text()).strip()
                    p = limpiar_precio(txt)
                    if p and p > 1000:
                        precio = p
                        break

            if nombre and precio:
                resultados.append({"nombre": nombre, "precio": precio, "tienda": nombre_tienda, "stock": "En stock", "url": ""})
        except Exception:
            pass

    return resultados


# ─── Utilidades ──────────────────────────────────────────────────────────────

def limpiar_precio(texto: str) -> float | None:
    """Extrae el precio numérico de un string."""
    texto = texto.replace("$", "").replace(".", "").replace(",", ".").strip()
    # Tomar el primer número grande que encuentre
    matches = re.findall(r'\d+\.?\d*', texto)
    for m in matches:
        try:
            val = float(m)
            if val > 500:  # descarta números chicos (ej: cantidades)
                return val
        except Exception:
            pass
    return None


async def scrape_tienda(page, tienda: dict, query: str, query_orig: str) -> list:
    """Busca en una tienda y devuelve resultados filtrados."""
    url = tienda["url"].format(query=query.replace(" ", "+"))
    print(f"  [{tienda['nombre']}] Buscando: '{query}'")

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
    except Exception as e:
        print(f"  [{tienda['nombre']}] ERROR: {e}")
        return []

    tipo = tienda["tipo"]
    if tipo == "compragamer":
        resultados = await parsear_compragamer(page)
    elif tipo == "mexx":
        resultados = await parsear_mexx(page)
    else:
        resultados = await parsear_generico(page, tienda["nombre"])

    # Filtrar por modelo
    relevantes = [r for r in resultados if es_relevante(r["nombre"], query, [query])]
    print(f"  [{tienda['nombre']}] {len(resultados)} encontrados → {len(relevantes)} relevantes")
    return relevantes


async def scrape_competidores(query: str, max_results: int = 10) -> list:
    """
    Busca en todas las tiendas competidoras.
    Retorna lista unificada de resultados ordenada por precio.
    """
    queries = construir_query(query)
    modelo = queries[0]  # usar la primera query como modelo de búsqueda
    print(f"[Competidores] Buscando: '{query}' → queries: {queries}")

    todos = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        for tienda in TIENDAS:
            try:
                resultados = await scrape_tienda(page, tienda, modelo, query)
                todos.extend(resultados)
                if len(todos) >= max_results:
                    break
            except Exception as e:
                print(f"  [{tienda['nombre']}] Error: {e}")
                continue

        await browser.close()

    # Deduplicar por (tienda + precio)
    vistos = set()
    unicos = []
    for r in todos:
        key = (r["tienda"].lower(), r["precio"])
        if key not in vistos:
            vistos.add(key)
            unicos.append(r)

    ordenados = sorted(unicos, key=lambda x: x["precio"])
    print(f"[Competidores] Total únicos: {len(ordenados)}")
    return ordenados


# ─── Test ─────────────────────────────────────────────────────────────────────

async def main():
    query = "Ryzen 5 5600GT"
    resultados = await scrape_competidores(query)

    print(f"\n{'='*60}")
    print(f"RESULTADOS COMPETIDORES — {len(resultados)}")
    print(f"{'='*60}")
    for i, r in enumerate(resultados, 1):
        print(f"  {i:2}. {r['nombre'][:45]:<45} | ${r['precio']:>12,.0f} | {r['tienda']}")


if __name__ == "__main__":
    asyncio.run(main())
    input("\nPresioná Enter para cerrar...")
