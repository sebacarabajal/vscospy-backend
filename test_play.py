#!/usr/bin/env python3
"""
test_vsco_playwright.py
Usa Playwright para actuar como un navegador real y bypasear Cloudflare
"""

# Instalar: pip install playwright
# Luego ejecutar: playwright install chromium

from playwright.sync_api import sync_playwright
import time
from PIL import Image, ExifTags, TiffImagePlugin
import io
from pprint import pprint

def cast(value):
    """Convierte valores no serializables a formatos compatibles con JSON."""
    if isinstance(value, TiffImagePlugin.IFDRational):
        return float(value)
    elif isinstance(value, tuple):
        return tuple(cast(t) for t in value)
    elif isinstance(value, bytes):
        return value.decode(errors="replace")
    elif isinstance(value, dict):
        return {kk: cast(vv) for kk, vv in value.items()}
    else:
        return value

def download_vsco_image(url):
    with sync_playwright() as p:
        # Lanzar navegador (headless=False para ver qué pasa)
        browser = p.chromium.launch(
            headless=True,  # Cambiar a False para debug
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # Crear contexto con user agent real
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
        )
        
        # Crear página
        page = context.new_page()
        
        print(f"Navegando a: {url}")
        
        # Interceptar respuestas para capturar la imagen
        image_data = None
        
        def handle_response(response):
            nonlocal image_data
            if response.url == url and response.status == 200:
                image_data = response.body()
                print(f"✅ Imagen capturada! Tamaño: {len(image_data)} bytes")
        
        # Escuchar respuestas
        page.on('response', handle_response)
        
        # Navegar a la URL
        response = page.goto(url, wait_until='networkidle', timeout=30000)
        
        print(f"Status inicial: {response.status}")
        
        # Esperar un poco para asegurar que todo cargue
        time.sleep(3)
        
        # Si no capturamos la imagen por respuesta, intentar otros métodos
        if not image_data:
            print("Intentando método alternativo...")
            
            # Método 2: Buscar elemento img en la página
            try:
                img_element = page.query_selector('img')
                if img_element:
                    img_src = img_element.get_attribute('src')
                    print(f"Imagen encontrada en DOM: {img_src}")
                    
                    # Descargar la imagen usando el contexto del navegador
                    img_response = page.goto(img_src if img_src != url else url)
                    image_data = img_response.body() if img_response else None
            except:
                pass
            
            # Método 3: Screenshot si es necesario
            if not image_data:
                print("Tomando screenshot como fallback...")
                page.screenshot(path='vsco_screenshot.png')
                print("Screenshot guardado como vsco_screenshot.png")
        
        browser.close()
        
        return image_data

# URL de prueba
TEST_URL = "https://img.vsco.co/0baa3b/57604661/67dc16ee388c7b71342fed40/vsco_032025.jpg"

print("="*60)
print("DESCARGA VSCO CON PLAYWRIGHT (NAVEGADOR REAL)")
print("="*60)

try:
    image_data = download_vsco_image(TEST_URL)
    
    if image_data:
        # Guardar imagen
        with open("vsco_playwright.jpg", "wb") as f:
            f.write(image_data)
        print(f"\n✅ Imagen guardada como 'vsco_playwright.jpg'")
        
        # Intentar obtener EXIF
        try:
            image = Image.open(io.BytesIO(image_data))
            print(f"Dimensiones: {image.size}")
            print(f"Formato: {image.format}")
            
            exif_data = image._getexif() or {}
            if exif_data:
                exif = {ExifTags.TAGS.get(k, k): cast(v) for k, v in exif_data.items()}
                print("\n📷 Datos EXIF encontrados:")
                pprint(exif)
            else:
                print("\n⚠️ No hay datos EXIF en esta imagen")
        except Exception as e:
            print(f"Error procesando imagen: {e}")
    else:
        print("\n❌ No se pudo descargar la imagen")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\n💡 Asegúrate de instalar playwright:")
    print("   pip install playwright")
    print("   playwright install chromium")