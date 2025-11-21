"""
vsco_handler.py
Módulo para manejar descargas de VSCO con Playwright
"""

from playwright.async_api import async_playwright
import asyncio
from typing import Optional, Tuple

class VSCOPlaywrightHandler:
    def __init__(self):
        self.playwright = None
        self.browser = None
        
    async def initialize(self):
        """Inicializa Playwright y el navegador"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            print("[VSCO Playwright] Navegador inicializado")
    
    async def close(self):
        """Cierra el navegador y Playwright"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def download_image(self, url: str) -> Optional[bytes]:
        """
        Descarga una imagen usando Playwright
        Retorna: image_data o None si falla
        """
        await self.initialize()
        
        context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
        )
        
        try:
            page = await context.new_page()
            print(f"[VSCO Playwright] Navegando a: {url}")
            
            image_data = None
            
            async def handle_response(response):
                nonlocal image_data
                if response.url == url and response.status == 200:
                    image_data = await response.body()
                    print(f"[VSCO Playwright] ✅ Imagen capturada! {len(image_data)} bytes")
            
            page.on('response', handle_response)
            response = await page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            if not image_data and response.status == 200:
                image_data = await response.body()
            
            return image_data
            
        finally:
            await context.close()

vsco_playwright = VSCOPlaywrightHandler()