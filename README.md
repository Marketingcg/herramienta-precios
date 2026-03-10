# Herramienta de Precios — Deploy en Render

## Pasos para subir a Render (gratis)

### 1. Subir el código a GitHub
1. Creá una cuenta en [github.com](https://github.com) si no tenés
2. Creá un **repositorio nuevo** (puede ser privado)
3. Subí todos estos archivos al repo:
   - `servidor.py`
   - `hardgamers_scraper.py`
   - `competidores_scraper.py`
   - `web.html`
   - `requirements.txt`
   - `build.sh`
   - `render.yaml`

### 2. Conectar con Render
1. Creá una cuenta en [render.com](https://render.com)
2. Click en **"New +"** → **"Web Service"**
3. Conectá tu cuenta de GitHub y elegí el repositorio
4. Completá así:
   - **Name:** herramienta-precios (o lo que quieras)
   - **Environment:** Python
   - **Build Command:** `bash build.sh`
   - **Start Command:** `uvicorn servidor:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free

5. Click en **"Create Web Service"**

### 3. Esperar el deploy
- El primer build tarda ~5-10 minutos (instala Playwright + Chromium)
- Una vez listo, tu app va a estar en: `https://tu-nombre.onrender.com`

## ⚠️ Limitaciones del plan gratuito
- Se "duerme" después de 15 minutos sin uso
- Al despertar tarda ~30-60 segundos en responder
- 512MB RAM (Playwright puede ser justo — si falla, hay que pagar $7/mes)

## Si falla por RAM
Probá Railway: [railway.app](https://railway.app) — $5/mes, más estable
