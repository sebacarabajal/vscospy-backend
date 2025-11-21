from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ExifTags, TiffImagePlugin
import io
import os
import sys
import httpx
import random
from pydantic import BaseModel
import traceback
from urllib.parse import urlparse, urlunparse 
from pprint import pprint 
import re

# Importar el handler de VSCO
from vsco_handler import vsco_playwright

app = FastAPI()

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)

class ImageUrl(BaseModel):
    url: str

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
    
def remove_query_params(url):
    parsed_url = urlparse(url)
    url_without_query = urlunparse(parsed_url._replace(query=''))
    return url_without_query

@app.on_event("shutdown")
async def shutdown_event():
    """Limpia recursos al cerrar"""
    await vsco_playwright.close()

@app.post("/getExifFromUrl/")
async def get_exif_from_url(image_url: ImageUrl):
    try:
        input_url = remove_query_params(image_url.url)
        print(f"INPUT URL: {input_url}")

        # ===== DETECCIÓN Y MANEJO DE VSCO =====
        vsco_pattern = r'https://im\.vsco\.co/aws-[^/]+/(.+)'
        vsco_match = re.match(vsco_pattern, input_url)
        
        if vsco_match:
            # ES UNA URL DE VSCO - USAR PLAYWRIGHT SIEMPRE
            path_after_region = vsco_match.group(1)
            final_url = f"https://img.vsco.co/{path_after_region}"
            print(f"VSCO URL detectada")
            print(f"  Región AWS: {input_url.split('/')[3]}")
            print(f"  URL transformada: {final_url}")
            
            # Usar Playwright directamente para VSCO
            image_data = await vsco_playwright.download_image(final_url)
            
            if not image_data:
                raise HTTPException(status_code=400, detail="No se pudo descargar la imagen de VSCO")
            
            # Procesar EXIF
            image = Image.open(io.BytesIO(image_data))
            exif_data = image._getexif() or {}
            exif = {ExifTags.TAGS.get(k, k): cast(v) for k, v in exif_data.items()}
            
            pprint(exif)
            return JSONResponse(content={"url": final_url, "EXIF": exif})
            
        else:
            # ===== NO ES VSCO - USAR MÉTODO TRADICIONAL (httpx) =====
            # Para otras URLs como imgur, flickr, etc. que funcionan bien con httpx
            
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:78.0) Gecko/20100101 Firefox/78.0",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36",
                "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0",
            ]

            headers = {'User-Agent': random.choice(user_agents)}

            async with httpx.AsyncClient(headers=headers, follow_redirects=False) as client:
                response = await client.get(input_url)
                print(f'status_code_1: {response.status_code}')

                urls_visited = [str(response.url)]
                while response.is_redirect:
                    response = await client.get(response.headers["Location"], headers=headers)
                    urls_visited.append(str(response.url))

                final_url = urls_visited[-1]
                print(f"FINAL URL: {final_url}")

                # Descargar la imagen desde la URL final
                response = await client.get(final_url, headers=headers)
                print(f'status_code_2: {response.status_code}')

                if response.status_code != 200:
                    raise HTTPException(status_code=400, detail=f"Error descargando la imagen. Status: {response.status_code}")

                # Procesar EXIF
                image = Image.open(io.BytesIO(response.content))
                exif_data = image._getexif() or {}
                exif = {ExifTags.TAGS.get(k, k): cast(v) for k, v in exif_data.items()}

                pprint(exif)
                return JSONResponse(content={"url": final_url, "EXIF": exif})
        
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        print(f'### Error getExifFromUrl: {e}')
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(f"Error: {e}, Type: {exc_type}, File: {fname}, Line: {exc_tb.tb_lineno}")
        return JSONResponse(content={"error": str(e)}, status_code=500)