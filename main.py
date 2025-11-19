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

app = FastAPI()

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lista los dominios si es necesario
    allow_credentials=True,
    allow_methods=["POST"],  # Métodos HTTP permitidos
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

@app.post("/getExifFromUrl/")
async def get_exif_from_url(image_url: ImageUrl):
    try:
        # Definir un array de posibles User-Agents
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:78.0) Gecko/20100101 Firefox/78.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A",
            "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko",
            "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko"
        ]

        # Seleccionar un User-Agent aleatoriamente
        headers = {'User-Agent': random.choice(user_agents)}

        async with httpx.AsyncClient(headers=headers, follow_redirects=False) as client:

            input_url = remove_query_params(image_url.url)
            print(f"INPUT URL: {input_url}")

            # ===== TRANSFORMACIÓN FLEXIBLE PARA VSCO =====
            # Detectar URLs de VSCO con cualquier región AWS
            # Patrón: https://im.vsco.co/aws-[región]/[path]
            vsco_pattern = r'https://im\.vsco\.co/aws-[^/]+/(.+)'
            vsco_match = re.match(vsco_pattern, input_url)
            
            if vsco_match:
                # Extraer el path después de la región AWS
                path_after_region = vsco_match.group(1)
                final_url = f"https://img.vsco.co/{path_after_region}"
                print(f"VSCO URL detectada (transformación flexible)")
                print(f"  Región AWS extraída: {input_url.split('/')[3]}")
                print(f"  URL transformada: {final_url}")
                
                # Intentar con la URL transformada
                response = await client.get(final_url, headers=headers)
                print(f'Status code VSCO: {response.status_code}')
                
                # Si falla con 403/404, podríamos intentar la original como fallback
                if response.status_code in [403, 404]:
                    print(f"Transformación falló con {response.status_code}, intentando URL original...")
                    response = await client.get(input_url, headers=headers)
                    print(f'Status code original: {response.status_code}')
                    final_url = input_url  # Si funciona la original, usar esa
                
            else:
                # ===== LÓGICA ORIGINAL PARA OTRAS URLs =====
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

            # ===== PROCESAMIENTO COMÚN =====
            if response.status_code != 200:
                if 'vsco.co' in input_url and response.status_code == 403:
                    error_msg = "VSCO está bloqueando la descarga (Cloudflare protection). Intenta más tarde."
                else:
                    error_msg = f"Error descargando la imagen. Status: {response.status_code}"
                raise HTTPException(status_code=400, detail=error_msg)

            # Procesar la imagen para obtener los metadatos EXIF
            image = Image.open(io.BytesIO(response.content))
            exif_data = image._getexif() or {}
            exif = {ExifTags.TAGS.get(k, k): cast(v) for k, v in exif_data.items()}

            pprint(exif)

            return JSONResponse(content={"url": final_url, "EXIF": exif})
        
    except Exception as e:
        traceback.print_exc()
        
        print('### Error getExifFromUrl: ' + str(e))
        
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(f"Error: {e}, Type: {exc_type}, File: {fname}, Line: {exc_tb.tb_lineno}")

        return JSONResponse(content={"error": str(e)}, status_code=500)