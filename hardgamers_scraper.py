"""
Scraper HardGamers — búsqueda universal inteligente
Estrategia: detectar el "núcleo identificador" de cualquier producto
como lo haría un humano que conoce el rubro.
"""

import asyncio
import re
from playwright.async_api import async_playwright

BASE_URL = "https://www.hardgamers.com.ar"

# ─── Conocimiento del dominio ────────────────────────────────────────────────

MARCAS_CONOCIDAS = {
    # Hardware
    "amd", "intel", "nvidia", "gigabyte", "asus", "msi", "asrock", "biostar",
    "corsair", "kingston", "crucial", "samsung", "adata", "xpg", "teamgroup", "gskill",
    "patriot", "hiksemi", "memox", "klevv",
    "seagate", "western", "wd", "sandisk", "kioxia", "lexar",
    "zotac", "palit", "evga", "powercolor", "sapphire", "xfx",
    "cooler", "gamemax", "lnz", "aorus", "seasonic", "thermaltake", "xpg",
    # Periféricos
    "logitech", "razer", "steelseries", "hyperx", "redragon", "genius",
    "a4tech", "antryx", "cougar", "sharkoon", "trust", "havit",
    # Monitores
    "lg", "aoc", "viewsonic", "benq", "dell", "hp", "philips", "performance",
    # Otros
    "sentey", "bangho", "noblex", "lenovo", "acer", "sony", "playstation", "performance", "perfomance",
    "deepcool", "noctua", "be quiet", "arctic", "thermaltake",
}

CHIPSETS_MB = [
    "z790", "z890", "z690", "z490", "z390", "z370", "z270", "z170",
    "b850m", "b850", "b760m", "b760", "b660", "b560", "b460",
    "b650m", "b650", "b550m", "b550", "b450m", "b450", "b350",
    "x870e", "x870", "x670e", "x670", "x570",
    "a620m", "a620", "a520m", "a520", "a320",
    "h610", "h670", "h510", "h410", "h310",
]

# Palabras que son RUIDO PURO — nunca identifican un producto
RUIDO_TOTAL = {
    "micro", "procesador", "microprocesador", "cpu",
    "memoria", "ram", "modulo",
    "disco", "solido", "rigido", "externo", "duro",
    "placa", "video", "grafica", "madre",
    "motherboard", "monitor", "fuente", "gabinete",
    "notebook", "laptop", "computadora", "pc",
    "teclado", "mouse", "combo", "auricular", "auriculares",
    "webcam", "camara", "microfono", "joystick", "gamepad", "control",
    "refrigeracion", "cooler", "disipador", "pasta",
    "de", "el", "la", "los", "las", "y", "con", "para", "sin", "del",
    "a", "e", "o", "en", "un", "una",
    "inalambrico", "inalámbrico", "wireless",
    "negro", "blanco", "black", "white", "silver", "rojo", "azul",
    "nuevo", "original", "box", "oem", "bulk", "open",
    "led", "argb", "rgb",
    "usb", "hdmi", "vga", "dp", "displayport",
    "lp", "slim", "mini", "micro",
    "similar",
}

# Palabras de specs que son importantes SOLO para ciertas categorías
SPECS_GENERICOS = {
    "ghz", "mhz", "mb", "gb", "tb",
    "am4", "am5", "lga1700", "lga1851", "lga1200", "lga1151", "s1700",
    "ddr4", "ddr5", "ddr3",
    "pcie", "nvme", "sata", "m.2",
    "80", "plus", "gold", "silver", "bronze", "platinum",
    "full", "modular", "semi",
    "fan", "rpm", "w", "watt",
    "fhd", "qhd", "uhd", "4k", "2k", "1080p",
    "hz", "ms", "ips", "va", "tn",
}


def limpiar(s):
    return s.lower().strip(".,;:-/()\"+\"")


def es_marca(palabra):
    return limpiar(palabra) in MARCAS_CONOCIDAS


def es_modelo_alfanumerico(palabra):
    """
    Detecta modelos tipo: K552, RM750e, G305, NV3, MP225V, MK235, C270, B550M
    Regla: mezcla letras y números, longitud 2-12, no es spec genérico
    """
    p = limpiar(palabra)
    if p in SPECS_GENERICOS or p in RUIDO_TOTAL:
        return False
    # Debe tener al menos una letra Y un número
    tiene_letra = bool(re.search(r'[a-z]', p))
    tiene_numero = bool(re.search(r'\d', p))
    if not (tiene_letra and tiene_numero):
        return False
    # Longitud razonable
    if len(p) < 2 or len(p) > 15:
        return False
    # No debe ser solo un spec (3200, 6000, etc)
    if re.match(r'^\d+$', p):
        return False
    return True


def detectar_categoria(query):
    q = query.lower()
    if any(k in q for k in ["notebook", "laptop"]):
        return "notebook"
    if any(k in q for k in ["memoria", " ram", "sodimm", "so-dimm"]):
        return "memoria"
    if any(k in q for k in ["disco solido", " ssd", "nvme", " m.2", "nv3", "nv2", "nv1"]):
        return "ssd"
    if any(k in q for k in ["disco rigido", "disco externo", " hdd", "skyhawk", "barracuda", "ironwolf"]):
        return "hdd"
    if any(k in q for k in ["motherboard", "placa madre"]):
        return "motherboard"
    if any(k in q for k in ["placa de video", "rtx", "gtx", " rx ", "geforce", "radeon", "video card"]):
        return "gpu"
    if any(k in q for k in ["ryzen", "core i", "core ultra", "i3-", "i5-", "i7-", "i9-",
                              "micro amd", "micro intel", "procesador"]):
        return "micro"
    if any(k in q for k in ["fuente", " psu "]):
        return "fuente"
    if any(k in q for k in ["monitor", " led ips", " led va"]):
        return "monitor"
    if any(k in q for k in ["gabinete", " case ", " torre "]):
        return "gabinete"
    if any(k in q for k in ["teclado"]):
        return "teclado"
    if any(k in q for k in ["mouse "," raton"]):
        return "mouse"
    if any(k in q for k in ["auricular", "headset", "headphone"]):
        return "auricular"
    if any(k in q for k in ["webcam", "camara web"]):
        return "webcam"
    if any(k in q for k in ["microfono", "micrófono"]):
        return "microfono"
    if any(k in q for k in ["joystick", "gamepad", "control ps", "dualsense", "dualshock"]):
        return "joystick"
    if any(k in q for k in ["combo teclado", "kit teclado"]):
        return "combo"
    if any(k in q for k in ["cooler", "disipador", "refrigeracion", "pasta termica", "ventilador"]):
        return "cooler"
    if any(k in q for k in ["pendrive", "pen drive", "flash"]):
        return "pendrive"
    return "general"


def extraer_marca(palabras, query):
    """Busca la marca en las palabras del query. Soporta marcas de dos palabras."""
    q = query.lower()
    # Marcas de dos palabras primero
    for marca_dos in ["cooler master", "be quiet", "western digital"]:
        if marca_dos in q:
            # Retornar capitalizada
            return marca_dos.title()
    for p in palabras:
        if limpiar(p) in MARCAS_CONOCIDAS:
            return p
    return None


def extraer_modelo_numerico(query):
    """
    Busca patrones de modelo numérico específico:
    i7-14700, Ryzen 5 5600, RTX 4070, etc.
    """
    q = query.lower()
    # Intel Core i
    m = re.search(r'(core\s+ultra\s+[579]\s+\d+\w*|i[3579][-\s]\d{4,5}\w*)', q, re.IGNORECASE)
    if m:
        modelo = m.group(0).strip()
        modelo = re.sub(r'(i[3579])\s+(\d)', r'\1-\2', modelo, flags=re.IGNORECASE)
        return modelo
    # AMD Ryzen
    m = re.search(r'ryzen\s+[3579]\s+\w+', q, re.IGNORECASE)
    if m:
        return m.group(0).strip()
    # RTX/GTX/RX + número
    m = re.search(r'(rtx|gtx|rx)\s+(\d{3,4})\s*(ti\s+super|super|ti|xtx|xt)?', q, re.IGNORECASE)
    if m:
        return m.group(0).strip().upper()
    return None


def construir_query(query):
    """
    Estrategia universal:
    1. Si tiene modelo numérico conocido (i7-14700, Ryzen 5 5600, RTX 4070) → usarlo directo
    2. Si tiene modelo alfanumérico (K552, RM750e, G305) → marca + modelo
    3. Si no → marca + atributos más específicos según categoría
    """
    cat = detectar_categoria(query)
    palabras = query.split()
    q = query.lower()

    # ── PRE-PASO: notebook siempre va por su propia lógica ──
    if cat == "notebook":
        partes = []
        marca = extraer_marca(palabras, query)
        if marca:
            partes.append(marca)
        excluir_nb = {"gb", "ssd", "ram", "hd", "usb", "m.2", "nvme", "intel", "amd",
                      "ghz", "mhz", "wifi", "bluetooth", "win11", "windows"}
        # Primero buscar nombres comerciales (solo letras, como "IdeaPad", "Vivobook", "MAX")
        nombres_comerciales = [p for p in palabras
                               if re.match(r'^[a-zA-Z]{3,}$', p)
                               and limpiar(p) not in excluir_nb
                               and limpiar(p) not in RUIDO_TOTAL
                               and limpiar(p) not in MARCAS_CONOCIDAS]
        # Luego modelos alfanuméricos cortos tipo "M5", "15ABA7"
        modelos_nb = [p for p in palabras if es_modelo_alfanumerico(p)
                      and not re.match(r'^i[3579]$', limpiar(p))
                      and not re.match(r'\d+(gb|tb)', limpiar(p))
                      and limpiar(p) not in excluir_nb]
        candidatos = nombres_comerciales[:1] + modelos_nb[:1]  # nombre + código
        if candidatos:
            partes.extend(candidatos)
            return [" ".join(dict.fromkeys(partes))]
        # Fallback: marca + procesador
        proc = extraer_modelo_numerico(query)
        if proc and marca:
            return [f"{marca} {proc}"]
        if proc:
            return [proc]
        if partes:
            return [" ".join(partes)]

    # ── PASO 1: modelo numérico específico ──
    modelo_num = extraer_modelo_numerico(query)
    if modelo_num:
        return [modelo_num]

    # ── PASO 2: chipset de motherboard (muy específico) ──
    if cat == "motherboard":
        chipset = next((c for c in CHIPSETS_MB if c in q), None)
        marca = extraer_marca(palabras, query)
        if chipset and marca:
            chipset_c = next((p for p in palabras if p.lower() == chipset), chipset.upper())
            return [f"{marca} {chipset_c}", chipset_c]
        elif chipset:
            chipset_c = next((p for p in palabras if p.lower() == chipset), chipset.upper())
            return [chipset_c]

    # ── PASO 3: modelo alfanumérico (solo para categorías sin lógica propia) ──
    marca = extraer_marca(palabras, query)
    CATS_CON_LOGICA_PROPIA = {"memoria", "ssd", "hdd", "fuente", "monitor",
                               "teclado", "notebook", "gabinete", "cooler",
                               "joystick", "pendrive", "gpu"}

    if cat not in CATS_CON_LOGICA_PROPIA:
        modelos_alfa = [p for p in palabras if es_modelo_alfanumerico(p)]
        if marca and modelos_alfa:
            modelo = max(modelos_alfa, key=lambda x: len(x))
            q1 = f"{marca} {modelo}"
            return [q1, modelo] if len(modelo) >= 3 else [q1]
        if modelos_alfa and not marca:
            modelo = max(modelos_alfa, key=lambda x: len(x))
            return [modelo]

    # ── PASO 4: sin modelo alfanumérico — construir por categoría ──

    if cat == "memoria":
        partes = []
        if marca:
            partes.append(marca)
        if "sodimm" in q:
            partes.append("Sodimm")
        submodelos_encontrados = []
        for sub in ["fury beast", "fury renegade", "fury", "beast", "vengeance", "ripjaws", "hiker", "lancer"]:
            if sub in q:
                submodelos_encontrados.append(sub.title())
                break  # solo el mas especifico
        partes.extend(submodelos_encontrados)
        cap = re.search(r'\b(\d+)\s*gb\b', q)
        if cap:
            partes.append(cap.group(1) + "GB")
        ddr = re.search(r'\b(ddr[3-5])\b', q, re.IGNORECASE)
        if ddr:
            partes.append(ddr.group(1).upper())
        vel = re.search(r'\b(\d{4,5})\s*mhz\b', q, re.IGNORECASE)
        if vel:
            partes.append(vel.group(1))
        if partes:
            q1 = " ".join(partes)
            # Segunda query sin velocidad por si no matchea exacto
            partes2 = [p for p in partes if not p.isdigit() or int(p) < 1000]
            q2 = " ".join(partes2) if partes2 != partes else None
            return [x for x in [q1, q2] if x]

    if cat in ("ssd", "hdd"):
        partes = []
        if marca:
            partes.append(marca)
        # Modelo alfanumérico del SSD: NV3, NV2, EVO, MX500, etc
        # Excluir capacidades (1TB, 240GB) — esas van aparte
        modelos_disco = [p for p in palabras if es_modelo_alfanumerico(p)
                         and not re.match(r'\d+(gb|tb)', p, re.IGNORECASE)
                         and limpiar(p) not in {"ssd", "hdd", "m.2", "nvme", "sata", "pcie",
                                                 "iii", "wd", "evo", "pro", "wave"}]
        if modelos_disco:
            partes.append(max(modelos_disco, key=len))
        cap = re.search(r'\b(\d+)\s*(gb|tb)\b', q, re.IGNORECASE)
        if cap:
            partes.append(cap.group(1) + cap.group(2).upper())
        for sub in ["skyhawk", "barracuda", "ironwolf", "evo", "pro", "wave"]:
            if sub in q:
                partes.append(sub.capitalize())
        if "externo" in q:
            partes.append("externo")
        if partes:
            return [" ".join(dict.fromkeys(partes))]

    if cat == "gpu":
        serie = next((s for s in ["rtx", "gtx", "rx", "arc", "gt"] if s in q), None)
        numero = re.search(r'\b(\d{3,4})\b', q)
        if serie and numero:
            s = serie.upper()
            n = numero.group(1)
            sufijo = ""
            for suf in ["ti super", "super", "xtx", "xt"]:
                if suf in q:
                    sufijo = " " + suf.upper()
                    break
            if not sufijo and (" ti " in q or q.endswith(" ti")):
                sufijo = " TI"
            q1 = f"{s} {n}{sufijo}".strip()
            marca = extraer_marca(palabras, query)
            if marca:
                return [q1, f"{marca} {q1}"]
            return [q1]

    if cat == "fuente":
        partes = []
        if marca:
            partes.append(marca)
        excluir_fuente = {"plus", "gold", "silver", "bronze", "platinum", "semi", "full",
                          "modular", "white", "black", "elite", "v3", "v2", "v4", "atx", "shift",
                          "pg5", "oem", "bulk", "incluye", "cable", "para", "pcie", "vhpwr",
                          "12vhpwr", "master", "mwe"}
        # Modelo alfanumérico (RM750e, FB550-LX) O nombre de modelo solo letras >= 4 (KYBER, MWE, ELITE)
        # Palabras de la marca para no incluirlas en el modelo
        palabras_marca = set(limpiar(m) for m in (marca or "").split())
        modelos_fuente = [p for p in palabras
                          if (es_modelo_alfanumerico(p) or (re.match(r'^[a-zA-Z]{4,}$', p) and len(p) <= 12))
                          and limpiar(p) not in excluir_fuente
                          and limpiar(p) not in RUIDO_TOTAL
                          and limpiar(p) not in MARCAS_CONOCIDAS
                          and limpiar(p) not in palabras_marca]
        if modelos_fuente:
            partes.append(max(modelos_fuente, key=len))
            return [" ".join(dict.fromkeys(partes))]
        # Fallback: marca + potencia
        pot = re.search(r'\b(\d{3,4})\s*w\b', q, re.IGNORECASE)
        if pot:
            partes.append(pot.group(1) + "W")
        if partes:
            return [" ".join(partes)]

    if cat == "monitor":
        partes = []
        if marca:
            partes.append(marca)
        # Modelo alfanumérico del monitor: MP225V, VA24EHF, etc
        modelos_mon = [p for p in palabras if es_modelo_alfanumerico(p)
                       and limpiar(p) not in {"fhd", "qhd", "uhd", "ips", "va", "tn", "led", "hdmi", "vga", "dp"}]
        if modelos_mon:
            partes.append(max(modelos_mon, key=len))
            return [" ".join(dict.fromkeys(partes))]
        # Fallback: marca + tamaño + hz
        tam = re.search(r'\b(\d{2})\s*(?:"|pulgadas)?\b', q)
        if tam and int(tam.group(1)) in range(15, 50):
            partes.append(tam.group(1) + '"')
        for res in ["144hz", "165hz", "240hz", "75hz", "100hz"]:
            if res in q:
                partes.append(res.upper())
        if partes:
            return [" ".join(partes)]

    if cat == "teclado":
        partes = []
        if marca:
            partes.append(marca)
        # Modelo alfanumérico del teclado (K552, TKL-X, G915, etc)
        modelos_tec = [p for p in palabras if es_modelo_alfanumerico(p)
                       and limpiar(p) not in {"tkl", "rgb", "argb", "usb", "ps2"}]
        if modelos_tec:
            partes.append(max(modelos_tec, key=len))
            return [" ".join(dict.fromkeys(partes))]
        # Sin modelo: usar switch + tamaño
        for sw in ["switch red", "switch blue", "switch brown", "switch yellow",
                   "red switch", "blue switch", "brown switch"]:
            if sw in q:
                partes.append(sw.replace("switch ", "").capitalize() + " Switch")
                break
        for tam in ["tkl", "60%", "tenkeyless"]:
            if tam in q:
                partes.append(tam.upper() if len(tam) <= 4 else tam.capitalize())
        if partes:
            return [" ".join(partes)]
        return ["teclado gamer " + (marca or "")]

    if cat == "gabinete":
        partes = []
        if marca:
            partes.append(marca)
        excluir_gab = {"fan", "x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8", "x9", "argb", "rgb",
                       "black", "white", "negro", "blanco", "mid", "tower", "atx", "matx", "itx"}
        for p in palabras:
            pl = limpiar(p)
            if pl in RUIDO_TOTAL or pl in SPECS_GENERICOS or pl in excluir_gab:
                continue
            if pl == limpiar(marca or ""):
                continue
            if len(pl) < 2:
                continue
            partes.append(p)
        if partes:
            return [" ".join(partes[:3])]

    if cat == "cooler":
        partes = []
        if marca:
            partes.append(marca)
        excluir_cooler = {"termica", "termic", "alto", "rendimiento", "pasta",
                          "refrigeracion", "disipador", "cooler", "ventilador",
                          limpiar(marca) if marca else ""}
        for p in palabras:
            pl = limpiar(p)
            if pl in RUIDO_TOTAL or pl in SPECS_GENERICOS or pl in excluir_cooler:
                continue
            if pl == limpiar(marca or ""):
                continue
            if len(p) > 2:
                partes.append(p)
        return [" ".join(dict.fromkeys(partes[:3]))] if partes else ["pasta termica" if "pasta" in q else "cooler"]

    if cat == "joystick":
        partes = []
        if marca:
            partes.append(marca)
        for consola in ["ps5", "ps4", "xbox", "dualsense", "dualshock"]:
            if consola in q:
                partes.append(consola.upper() if len(consola) <= 4 else consola.capitalize())
        if partes:
            return [" ".join(partes)]

    if cat == "pendrive":
        partes = []
        if marca:
            partes.append(marca)
        cap = re.search(r'\b(\d+)\s*(gb|tb)\b', q, re.IGNORECASE)
        if cap:
            partes.append(cap.group(1) + cap.group(2).upper())
        return [" ".join(partes)] if partes else ["pendrive"]

    # ── PASO 5: fallback universal ──
    # Quedarse con marca + palabras que no son ruido, ordenadas por especificidad
    candidatos = []
    for p in palabras:
        pl = limpiar(p)
        if pl in RUIDO_TOTAL or pl in SPECS_GENERICOS:
            continue
        if len(pl) < 2:
            continue
        candidatos.append(p)

    if candidatos:
        return [" ".join(candidatos[:4])]

    # Último recurso: todo el query limpio
    return [query]


def es_relevante(nombre, query_original, queries_usadas=None):
    """
    Verifica que el resultado sea realmente el producto buscado.
    Flexible: cuantas más palabras de la query aparecen, mejor.
    """
    if queries_usadas is None:
        queries_usadas = construir_query(query_original)

    nombre_up = nombre.upper()

    for q in queries_usadas:
        partes = [p.upper() for p in q.split() if len(p) >= 2]
        if not partes:
            continue
        matches = sum(1 for p in partes if p in nombre_up)
        # Para 1 palabra: exacto. Para 2: ambas. Para 3+: mayoría
        if len(partes) == 1:
            umbral = 1
        elif len(partes) == 2:
            umbral = 2
        else:
            umbral = max(2, len(partes) * 2 // 3)

        if matches >= umbral:
            return True

    return False


# Alias para compatibilidad con competidores_scraper
def extraer_modelo(query):
    return construir_query(query)[0]


async def _buscar(page, query, max_items):
    search_url = f"{BASE_URL}/search?text={query.replace(' ', '+')}&page=1&limit=50"
    print(f"  → Buscando: '{query}'")
    try:
        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        print(f"  [ERROR] {e}")
        return []
    try:
        await page.wait_for_function(
            """() => {
                const el = document.querySelector('#searchInfo span');
                return el && el.innerText && !el.innerText.includes('0 result');
            }""",
            timeout=12000
        )
    except Exception:
        pass
    await page.wait_for_timeout(1500)
    items = await page.query_selector_all("article.product")
    resultados = []
    for item in items[:max_items]:
        try:
            is_highlighted = await item.evaluate("el => !!el.closest('#store-highlighted')")
            if is_highlighted:
                continue
            name = ""
            el = await item.query_selector("h3.product-title")
            if el:
                name = (await el.inner_text()).strip()
            price_num = None
            el = await item.query_selector('[itemprop="price"]')
            if el:
                price_raw = (await el.get_attribute("content")) or (await el.inner_text()).strip()
                try:
                    price_num = float(price_raw.replace(".", "").replace(",", ".").replace("$", "").strip())
                except ValueError:
                    pass
            store = ""
            el = await item.query_selector("h4.subtitle")
            if el:
                store = (await el.inner_text()).strip()
            stock = ""
            el = await item.query_selector('[itemprop="availability"]')
            if el:
                href = await el.get_attribute("href") or ""
                stock = "En stock" if "InStock" in href else "Sin stock"
            url = ""
            el = await item.query_selector('[itemprop="url"]')
            if el:
                href = await el.get_attribute("href") or ""
                url = href if href.startswith("http") else BASE_URL + href
            if price_num and name:
                resultados.append({"nombre": name, "precio": price_num,
                                   "tienda": store, "stock": stock, "url": url})
        except Exception as e:
            print(f"  [WARN] {e}")
    print(f"  → {len(resultados)} encontrados")
    return resultados



def construir_query_fallback(query, nivel):
    """
    Genera queries progresivamente más amplias para cuando la específica no da resultados.
    nivel 1: sin modelo, solo marca + atributos básicos
    nivel 2: solo categoría + atributo más básico (capacidad, serie, etc)
    """
    cat = detectar_categoria(query)
    palabras = query.split()
    q = query.lower()
    marca = extraer_marca(palabras, query)

    if nivel == 1:
        # Marca + atributo principal (sin modelo específico)
        if cat == "memoria":
            cap = re.search(r'\b(\d+)\s*gb\b', q)
            ddr = re.search(r'\b(ddr[3-5])\b', q, re.IGNORECASE)
            partes = []
            if marca: partes.append(marca)
            if cap: partes.append(cap.group(1) + "GB")
            if ddr: partes.append(ddr.group(1).upper())
            return " ".join(partes) if partes else None

        if cat in ("ssd", "hdd"):
            cap = re.search(r'\b(\d+)\s*(gb|tb)\b', q, re.IGNORECASE)
            partes = []
            if marca: partes.append(marca)
            if cap: partes.append(cap.group(1) + cap.group(2).upper())
            if cat == "ssd": partes.append("SSD")
            if "externo" in q: partes.append("externo")
            return " ".join(partes) if partes else None

        if cat == "gpu":
            serie = next((s for s in ["rtx", "gtx", "rx", "gt"] if s in q), None)
            numero = re.search(r'\b(\d{3,4})\b', q)
            if serie and numero:
                return f"{serie.upper()} {numero.group(1)}"
            if marca: return marca
            return None

        if cat == "motherboard":
            chipset = next((c for c in CHIPSETS_MB if c in q), None)
            if chipset: return chipset.upper()
            if marca: return marca
            return None

        if cat == "micro":
            modelo = extraer_modelo_numerico(query)
            if modelo: return modelo
            return None

        if cat == "fuente":
            pot = re.search(r'\b(\d{3,4})\s*w\b', q, re.IGNORECASE)
            partes = []
            if marca: partes.append(marca)
            if pot: partes.append(pot.group(1) + "W")
            return " ".join(partes) if partes else None

        if cat == "monitor":
            tam = re.search(r'\b(\d{2})\b', q)
            partes = []
            if marca: partes.append(marca)
            if tam and int(tam.group(1)) in range(15, 50):
                partes.append(tam.group(1) + "\"")
            return " ".join(partes) if partes else None

        if cat == "notebook":
            if marca: return marca
            return None

        # Generico: solo marca
        if marca: return marca
        return None

    if nivel == 2:
        # Solo el atributo más básico — sin marca
        if cat == "memoria":
            cap = re.search(r'\b(\d+)\s*gb\b', q)
            ddr = re.search(r'\b(ddr[3-5])\b', q, re.IGNORECASE)
            partes = []
            if cap: partes.append(cap.group(1) + "GB")
            if ddr: partes.append(ddr.group(1).upper())
            if partes: return "memoria " + " ".join(partes)
            return None

        if cat in ("ssd", "hdd"):
            cap = re.search(r'\b(\d+)\s*(gb|tb)\b', q, re.IGNORECASE)
            tipo = "SSD" if cat == "ssd" else "disco externo" if "externo" in q else "HDD"
            if cap: return f"{tipo} {cap.group(1)}{cap.group(2).upper()}"
            return tipo

        if cat == "gpu":
            serie = next((s for s in ["rtx", "gtx", "rx", "gt"] if s in q), None)
            if serie: return f"placa {serie.upper()}"
            return "placa de video"

        if cat == "monitor":
            tam = re.search(r'\b(\d{2})\b', q)
            if tam and int(tam.group(1)) in range(15, 50):
                return f"monitor {tam.group(1)}\""
            return "monitor"

        if cat == "fuente":
            pot = re.search(r'\b(\d{3,4})\s*w\b', q, re.IGNORECASE)
            if pot: return f"fuente {pot.group(1)}W"
            return "fuente"

        if cat == "notebook":
            return "notebook"

        if cat == "teclado": return "teclado gamer"
        if cat == "mouse": return "mouse gamer"
        if cat == "auricular": return "auriculares gamer"

        # Ultimo recurso: usar las primeras palabras no-ruido
        candidatos = [p for p in palabras if limpiar(p) not in RUIDO_TOTAL and len(p) > 2]
        return " ".join(candidatos[:2]) if candidatos else None

    return None

async def scrape_hardgamers(query, max_results=50):
    queries = construir_query(query)
    print(f"[HardGamers] '{query}'")
    print(f"[HardGamers] Queries: {queries}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ))
        page = await context.new_page()

        # Intento 1 — queries específicas
        todos = []
        for q in queries:
            r = await _buscar(page, q, max_results)
            todos.extend(r)
        relevantes = _filtrar_y_deduplicar(todos, query, queries)

        # Intento 2 — fallback nivel 1 (más amplio, sin modelo)
        if not relevantes:
            fb1 = construir_query_fallback(query, 1)
            if fb1 and fb1.lower() not in [q.lower() for q in queries]:
                print(f"[HardGamers] Sin resultados → fallback 1: '{fb1}'")
                r = await _buscar(page, fb1, max_results)
                relevantes = _filtrar_y_deduplicar(r, query, [fb1])

        # Intento 3 — fallback nivel 2 (muy amplio, solo categoría + atributo básico)
        if not relevantes:
            fb2 = construir_query_fallback(query, 2)
            if fb2 and fb2 != construir_query_fallback(query, 1):
                print(f"[HardGamers] Sin resultados → fallback 2: '{fb2}'")
                r = await _buscar(page, fb2, max_results)
                # En fallback 2 no filtramos por relevancia — devolvemos todo lo que haya
                relevantes = _filtrar_y_deduplicar(r, query, [fb2], filtro_suave=True)

        await browser.close()

    print(f"[HardGamers] Resultado final: {len(relevantes)} únicos")
    return relevantes


def _filtrar_y_deduplicar(resultados, query_original, queries_usadas, filtro_suave=False):
    """Filtra por relevancia y deduplica por (tienda, precio)."""
    if filtro_suave:
        relevantes = resultados  # en fallback 2 no filtramos
    else:
        relevantes = [r for r in resultados if es_relevante(r["nombre"], query_original, queries_usadas)]
    vistos = set()
    unicos = []
    for r in relevantes:
        key = (r["tienda"].lower().strip(), r["precio"])
        if key not in vistos:
            vistos.add(key)
            unicos.append(r)
    return unicos


async def main():
    casos = [
        # Tu lista real
        "Motherboard GIGABYTE Z790 D DDR4 S1700",
        "Disco Solido SSD 240GB Hiksemi Wave SATA III",
        "Disco Solido SSD 1TB Kingston NV3 M.2 NVMe PCIe x4 4.0 6000 MB/s",
        "Disco Externo 4Tb Seagate USB",
        "Micro AMD Ryzen 5 5600 Ghz AM4",
        "Core i9-14900F 5.9 GHz 36Mb S.1700",
        "Core Ultra 7 265F 3.9 GHz LGA1851",
        "Memoria RAM Kingston Fury Beast 8GB 6000 Mhz CL36 DDR5",
        "Memoria Ram Sodimm Hiksemi 8GB 3200 Mhz DDR4",
        "Fuente 750W Corsair RM750e 2025 80 PLUS Gold Full Modular",
        "Fuente LNZ 550W FB550-LX OEM Bulk",
        "Placa de Video MSI Nvidia Geforce Rtx 5070 Shadow X2 12gb Oc Gddr7",
        "Monitor LED IPS 22 MSI Pro MP225V FHD 100Hz 1ms HDMI VGA",
        "Gabinete Sentey Zeus Black Fan x5 Argb",
        "Gabinete LNZ Y10 Fan x4 Argb",
        "Notebook Bangho MAX M5 i3 15.6 Intel I3 1215U 8GB Ram 240GB SSD",
        "Refrigeracion Pasta Termica Corsair XTM60 Alto Rendimiento",
        "Microfono Kingston HyperX QuadCast 2",
        "Combo Teclado Y Mouse Logitech MK235 Inalambrico",
        "Mouse Logitech G305 Lightspeed Inalambrico White",
        "Webcam Logitech C270 HD 720P",
        "Joystick Sony Playstation PS5 DualSense Controller Midnight Black",
        # Casos con modelo alfanumérico genérico
        "Teclado Gamer Redragon Kumara K552 RGB Switch Red",
        "Teclado Gamer Switch Blue TKL Sin Marca",
        "Auriculares HyperX Cloud Alpha S 7.1",
        "Pendrive Kingston 64GB USB 3.0",
    ]
    print(f"\n{'CAT':<12} {'QUERIES':<55} PRODUCTO")
    print("-" * 115)
    for c in casos:
        qs = construir_query(c)
        cat = detectar_categoria(c)
        print(f"{cat:<12} {str(qs):<55} {c[:50]}")


if __name__ == "__main__":
    asyncio.run(main())
    input("\nPresioná Enter para cerrar...")
